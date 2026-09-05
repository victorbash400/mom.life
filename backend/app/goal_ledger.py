import json
from uuid import uuid4


class GoalLedger:
    """Transactional plan revisions and the durable human handoff ledger."""

    def apply_plan(self, family_id, goal_id, operations):
        from app.task_store import now
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            goal = db.execute("SELECT * FROM family_tasks WHERE id=? AND family_id=?", (goal_id, family_id)).fetchone()
            if not goal or goal['status'] != 'active':
                raise ValueError('Goal is missing or no longer active.')
            rows = {r['id']: dict(r) for r in db.execute('SELECT * FROM goal_assignments WHERE goal_id=?', (goal_id,))}
            skills = {r['id'] for r in db.execute('SELECT id FROM family_skills WHERE family_id=?', (family_id,))}
            keys = {}
            for op in operations:
                action = op.action
                if any(s not in skills for s in op.skill_ids):
                    raise ValueError('Plan selected an unknown family skill.')
                if action == 'create':
                    if not op.key or op.key in keys or not op.title.strip() or not op.instruction.strip() or not op.expected_outputs:
                        raise ValueError('New assignments require a unique key, title, instruction and expected outputs.')
                    if any(r['title'].casefold() == op.title.casefold() and r['status'] != 'cancelled' for r in rows.values()):
                        raise ValueError('Revise the existing assignment instead of duplicating its outcome.')
                    deps = [keys.get(d, d) for d in op.depends_on]
                    if any(d not in rows for d in deps):
                        raise ValueError('Dependencies must refer to existing tasks or earlier create keys.')
                    task_id = str(uuid4())
                    db.execute('''INSERT INTO goal_assignments
                        (id,goal_id,title,instruction,status,phase,current_step,depends_on,required_inputs,expected_outputs,skill_ids,created_at)
                        VALUES (?,?,?,?,'queued','queued',?,?,?,?,?,?)''',
                        (task_id,goal_id,op.title,op.instruction,op.title,json.dumps(deps),json.dumps(op.required_inputs),json.dumps(op.expected_outputs),json.dumps(op.skill_ids),now()))
                    rows[task_id] = {'id':task_id,'title':op.title,'status':'queued'}
                    keys[op.key] = task_id
                    continue
                row = rows.get(op.task_id)
                if not row:
                    raise ValueError('Plan referenced a task outside this goal.')
                if action == 'reuse':
                    continue
                if row['status'] == 'completed':
                    raise ValueError('Completed evidence cannot be rewritten or cancelled.')
                db.execute("UPDATE goal_questions SET state='superseded' WHERE assignment_id=? AND state IN ('open','approved')", (op.task_id,))
                if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='provider_waits'").fetchone():
                    db.execute("UPDATE provider_waits SET state='superseded' WHERE assignment_id=? AND state='waiting'", (op.task_id,))
                if action == 'cancel':
                    db.execute("UPDATE goal_assignments SET status='cancelled',phase='cancelled',finished_at=? WHERE id=?", (now(),op.task_id))
                    row['status'] = 'cancelled'
                    continue
                if action == 'steer' and row['status'] not in {'running','blocked','queued'}:
                    raise ValueError('Only running or blocked assignments can be steered.')
                if action == 'retry' and row['status'] != 'failed':
                    raise ValueError('Retry must target the same failed assignment.')
                if not op.instruction.strip():
                    raise ValueError('A revision requires the complete corrected instruction.')
                db.execute("UPDATE goal_assignments SET instruction=?,status='queued',phase='queued',finished_at=NULL,current_step='Ready to continue' WHERE id=?", (op.instruction,op.task_id))
                row['status'] = 'queued'
                if 'depends_on' in op.model_fields_set:
                    deps = [keys.get(identity, identity) for identity in op.depends_on]
                    db.execute('UPDATE goal_assignments SET depends_on=? WHERE id=?',(json.dumps(deps),op.task_id))
                for name, value in [('title',op.title),('expected_outputs',op.expected_outputs),('required_inputs',op.required_inputs),('skill_ids',op.skill_ids)]:
                    if value or name in {'required_inputs','skill_ids'} and name in op.model_fields_set:
                        db.execute(f'UPDATE goal_assignments SET {name}=? WHERE id=?', (json.dumps(value) if isinstance(value,list) else value,op.task_id))
            from app.plan_validation import validate_dependencies
            validate_dependencies(db.execute('SELECT * FROM goal_assignments WHERE goal_id=?',(goal_id,)).fetchall())
            db.execute("UPDATE family_tasks SET run_state='queued',updated_at=? WHERE id=?", (now(),goal_id))

    def question(self, goal_id, assignment_id, question, context='', action=None):
        from app.task_store import now
        action_json = json.dumps(action, sort_keys=True) if action else ''
        with self._connect() as db:
            existing = db.execute("SELECT id FROM goal_questions WHERE assignment_id=? AND question=? AND action=? AND state='open'", (assignment_id,question,action_json)).fetchone()
            if existing:
                return existing['id']
            identity = str(uuid4())
            db.execute('INSERT INTO goal_questions VALUES (?,?,?,?,?,?,?, ?,?,?)', (identity,goal_id,assignment_id,question,context,action_json,'open','',now(),None))
            return identity

    def answer_question(self, family_id, goal_id, question_id, answer, approved=False):
        from app.task_store import now
        with self._connect() as db:
            row = db.execute('SELECT q.* FROM goal_questions q JOIN family_tasks g ON g.id=q.goal_id WHERE q.id=? AND q.goal_id=? AND g.family_id=?', (question_id,goal_id,family_id)).fetchone()
            if not row or row['state'] != 'open':
                raise ValueError('Question is missing or already answered.')
            if not answer.strip():
                raise ValueError('An answer is required.')
            state = 'approved' if approved and row['action'] else 'answered'
            db.execute('UPDATE goal_questions SET answer=?,state=?,answered_at=? WHERE id=?', (answer,state,now(),question_id))
            db.execute("UPDATE goal_assignments SET status='queued',phase='queued',finished_at=NULL WHERE id=? AND status='blocked'", (row['assignment_id'],))
            db.execute("UPDATE family_tasks SET status='active',run_state='queued',updated_at=? WHERE id=?", (now(),goal_id))

    def consume_approval(self, assignment_id, action):
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT id FROM goal_questions WHERE assignment_id=? AND action=? AND state='approved' ORDER BY created_at LIMIT 1", (assignment_id,json.dumps(action,sort_keys=True))).fetchone()
            if not row:
                return False
            db.execute("UPDATE goal_questions SET state='consumed' WHERE id=?", (row['id'],))
            return True

    def questions(self, goal_id):
        with self._connect() as db:
            return [{**dict(r),'action':json.loads(r['action']) if r['action'] else None} for r in db.execute('SELECT * FROM goal_questions WHERE goal_id=? ORDER BY created_at', (goal_id,))]

    def save_skill(self, family_id, payload, skill_id=None):
        from app.task_store import now
        identity = skill_id or str(uuid4())
        with self._connect() as db:
            if skill_id:
                row = db.execute('SELECT id FROM family_skills WHERE id=? AND family_id=?', (identity,family_id)).fetchone()
                if not row:
                    raise ValueError('Skill not found.')
                db.execute('UPDATE family_skills SET name=?,description=?,instructions=?,required_plugin_ids=?,version=version+1 WHERE id=?', (payload.name,payload.description,payload.instructions,json.dumps(payload.required_plugin_ids),identity))
            else:
                db.execute('INSERT INTO family_skills VALUES (?,?,?,?,?,?,?,?,?,?)', (identity,family_id,identity,payload.name,payload.description,payload.instructions,json.dumps(payload.required_plugin_ids),'custom',1,now()))
        return identity

    def recover(self):
        from app.runtime_lock import acquire, release
        with self._connect() as db:
            identities = [r['id'] for r in db.execute("SELECT id FROM family_tasks WHERE status='active' AND run_state IN ('planning','queued','running')")]
        for identity in identities:
            lease = acquire(self.path,identity)
            if lease is None:
                continue
            try:
                with self._connect() as db:
                    db.execute("UPDATE family_tasks SET status='paused',run_state='paused' WHERE id=?", (identity,))
                    db.execute("UPDATE goal_assignments SET status='queued',phase='queued' WHERE status='running' AND goal_id=?", (identity,))
            finally:
                release(lease)

    def family_context(self, family_id):
        with self._connect() as db:
            row = db.execute('SELECT payload FROM family_context WHERE family_id=?',(family_id,)).fetchone()
            return json.loads(row['payload']) if row else {"family_id":family_id,"note":"No family profile has been supplied. Ask Mom for missing facts."}

    def save_family_context(self, family_id, payload):
        with self._connect() as db:
            db.execute('INSERT OR REPLACE INTO family_context VALUES (?,?)',(family_id,json.dumps(payload)))
