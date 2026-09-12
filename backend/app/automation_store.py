"""Small durable automation ledger. AWS and application events share the same inbox."""
import json
from contextlib import nullcontext
from uuid import uuid4

from app.database import Connection
from app.task_store import now


class AutomationStore:
    def __init__(self, tasks):
        self.tasks = tasks

    def initialize(self):
        with self.tasks._connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS automations (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL,
                    goal_id TEXT NOT NULL REFERENCES family_tasks(id) ON DELETE CASCADE,
                    instruction TEXT NOT NULL, trigger TEXT NOT NULL,
                    schedule TEXT NOT NULL DEFAULT '', timezone TEXT NOT NULL DEFAULT 'UTC',
                    enabled INTEGER NOT NULL DEFAULT 0, version INTEGER NOT NULL DEFAULT 1,
                    scheduler_state TEXT NOT NULL DEFAULT 'pending', failure TEXT NOT NULL DEFAULT '',
                    last_checked_at TEXT, last_result TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS automation_wakes (
                    id TEXT PRIMARY KEY, automation_id TEXT NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL, context TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending',
                    run_goal_id TEXT REFERENCES family_tasks(id) ON DELETE SET NULL,
                    created_at TEXT NOT NULL, finished_at TEXT, failure TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS automation_run_links (
                    run_goal_id TEXT PRIMARY KEY REFERENCES family_tasks(id) ON DELETE CASCADE,
                    automation_id TEXT NOT NULL, version INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS automation_wakes_pending ON automation_wakes(state,created_at);
                CREATE TABLE IF NOT EXISTS automation_notifications (
                    id TEXT PRIMARY KEY, wake_id TEXT NOT NULL UNIQUE REFERENCES automation_wakes(id) ON DELETE CASCADE,
                    family_id TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL,
                    read_at TEXT
                );
            ''')

    def list(self, family_id, connection=None):
        with nullcontext(connection) if connection is not None else self.tasks._connect() as db:
            rows = db.execute('''SELECT a.*, g.child_id,g.text AS task_text,g.status AS task_status
                FROM automations a JOIN family_tasks g ON g.id=a.goal_id
                WHERE a.family_id=? ORDER BY a.created_at DESC''', (family_id,)).fetchall()
            return [{**dict(row), 'enabled': bool(row['enabled'])} for row in rows]

    def get(self, family_id, automation_id, connection=None):
        with nullcontext(connection) if connection is not None else self.tasks._connect() as db:
            row = db.execute("""SELECT a.*,g.child_id,g.text AS task_text,g.status AS task_status
                FROM automations a JOIN family_tasks g ON g.id=a.goal_id
                WHERE a.family_id=? AND a.id=?""", (family_id,automation_id)).fetchone()
        return {**dict(row),'enabled':bool(row['enabled'])} if row else None

    def create(self, family_id, goal_id, instruction, trigger, schedule='', timezone='UTC', enabled=False, scheduler_state='pending'):
        identity = str(uuid4())
        with self.tasks._connect() as db:
            goal = db.execute('SELECT id FROM family_tasks WHERE family_id=? AND id=?', (family_id,goal_id)).fetchone()
            if not goal:
                raise ValueError('Select a task belonging to this family.')
            db.execute('''INSERT INTO automations
                (id,family_id,goal_id,instruction,trigger,schedule,timezone,enabled,scheduler_state,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)''', (identity,family_id,goal_id,instruction,trigger,schedule,timezone,int(enabled),scheduler_state,now()))
            return self.get(family_id, identity, db)

    def enqueue(self, automation_id, version, event_id, context, connection=None):
        with nullcontext(connection) if connection is not None else self.tasks._connect() as db:
            if connection is None:
                db.execute('BEGIN IMMEDIATE')
            item = db.execute('''SELECT a.*,g.status FROM automations a JOIN family_tasks g ON g.id=a.goal_id
                WHERE a.id=? AND a.version=? AND a.enabled=1 AND g.status!='paused' ''', (automation_id,version)).fetchone()
            if not item:
                return False
            inserted = db.execute('''INSERT INTO automation_wakes(id,automation_id,version,context,created_at)
                VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING''',
                (f'{automation_id}:{version}:{event_id}', automation_id,version,json.dumps(context,default=str),now())).rowcount
            if inserted and isinstance(db, Connection):
                db.execute("SELECT pg_notify('mom_life_automations',?)", (item['goal_id'],))
            return bool(inserted)

    def enqueue_event(self, family_id, child_ids, trigger, event_id, context, connection=None):
        goals = set()
        for item in self.list(family_id,connection):
            if item['trigger'] == trigger and (not child_ids or "" in child_ids or item['child_id'] == 'all' or item['child_id'] in child_ids):
                if self.enqueue(item['id'],item['version'],event_id,context,connection):
                    goals.add(item['goal_id'])
        return goals

    def pending_goals(self):
        with self.tasks._connect() as db:
            return [dict(row) for row in db.execute('''SELECT DISTINCT a.family_id,a.goal_id
                FROM automations a JOIN automation_wakes w ON w.automation_id=a.id
                JOIN family_tasks g ON g.id=a.goal_id
                WHERE a.enabled=1 AND w.version=a.version AND w.state IN ('pending','running','blocked')
                AND g.status!='paused' ''').fetchall()]

    def next_wake(self, family_id, goal_id):
        with self.tasks._connect() as db:
            row = db.execute('''SELECT w.*,a.instruction,a.last_checked_at,a.last_result,a.trigger
                FROM automation_wakes w JOIN automations a ON a.id=w.automation_id
                WHERE a.family_id=? AND a.goal_id=? AND a.enabled=1 AND a.version=w.version
                AND w.state IN ('pending','running','blocked') ORDER BY w.created_at,w.id LIMIT 1''',
                (family_id,goal_id)).fetchone()
            return dict(row) if row else None

    def begin(self, wake, parent):
        """Create the bounded run and its pointer atomically; recovery reuses this run."""
        identity = str(uuid4())
        context = {'automation_instruction': wake['instruction'], 'task': parent['text'],
                   'child_id': parent['child_id'], 'last_checked_at': wake['last_checked_at'],
                   'last_result': wake['last_result'], 'trigger': wake['trigger'],
                   'new_information': json.loads(wake['context'])}
        request = 'Perform one automation check using this saved context. Act only if necessary under the instruction. '
        request += 'Use notify_mom for a requested in-app notification when its condition is met. Do not create another automation.\n'
        request += json.dumps(context,default=str)
        with self.tasks._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current = db.execute('''SELECT w.run_goal_id FROM automation_wakes w JOIN automations a ON a.id=w.automation_id
                JOIN family_tasks g ON g.id=a.goal_id WHERE w.id=? AND a.enabled=1 AND a.version=w.version
                AND g.status!='paused' ''', (wake['id'],)).fetchone()
            if not current:
                return None
            if current['run_goal_id']:
                return current['run_goal_id']
            created_at = now()
            db.execute('''INSERT INTO family_tasks(id,family_id,child_id,text,status,created_at,updated_at,run_state,current_step)
                VALUES (?,?,?,?,'active',?,?,'queued','Ready to check')''',
                (identity,parent['family_id'],parent['child_id'],request,created_at,created_at))
            assignment_id = str(uuid4())
            db.execute('''INSERT INTO goal_assignments
                (id,goal_id,title,instruction,status,phase,current_step,depends_on,required_inputs,expected_outputs,skill_ids,created_at)
                VALUES (?,?,'Automation check',?,'queued','queued','Automation check','[]','[]',?,'[]',?)''',
                (assignment_id,identity,request,json.dumps(['Automation check result']),created_at))
            db.execute("INSERT INTO automation_run_links VALUES (?,?,?)", (identity,wake["automation_id"],wake["version"]))
            db.execute("UPDATE automation_wakes SET run_goal_id=?,state='running' WHERE id=?", (identity,wake['id']))
        return identity

    def finish(self, wake, run):
        state = 'completed' if run['status'] == 'completed' else 'failed' if run['run_state'] == 'failed' else 'blocked'
        result = run['report'] or run['current_step']
        with self.tasks._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            active = db.execute('''SELECT a.schedule,a.goal_id FROM automation_wakes w JOIN automations a ON a.id=w.automation_id
                WHERE w.id=? AND a.enabled=1 AND a.version=w.version AND w.state!='cancelled' ''', (wake['id'],)).fetchone()
            if not active:
                return 'cancelled'
            db.execute('UPDATE automation_wakes SET state=?,finished_at=?,failure=? WHERE id=?',
                       (state, now() if state != 'blocked' else None,result if state == 'failed' else '',wake['id']))
            if state in {'completed','failed'}:
                db.execute('UPDATE automations SET last_checked_at=?,last_result=?,failure=? WHERE id=? AND version=?',
                           (now(),result,result if state == 'failed' else '',wake['automation_id'],wake['version']))
                if active['schedule'].startswith('at('):
                    db.execute("UPDATE automations SET enabled=0,scheduler_state=? WHERE id=? AND version=?",
                               (state,wake['automation_id'],wake['version']))
            if isinstance(db, Connection):
                db.execute("SELECT pg_notify('mom_life_automations',?)", (active['goal_id'],))
        return state

    def require_active_run(self, run_goal_id):
        with self.tasks._connect() as db:
            wake = db.execute('''SELECT a.enabled,a.version,w.version AS wake_version,g.status
                FROM automation_run_links w LEFT JOIN automations a ON a.id=w.automation_id
                LEFT JOIN family_tasks g ON g.id=a.goal_id WHERE w.run_goal_id=?''', (run_goal_id,)).fetchone()
        if wake and (not wake['enabled'] or wake['version'] != wake['wake_version'] or wake['status'] == 'paused'):
            raise ValueError('This automation was paused or changed. Stop this check.')

    def notify(self, run_goal_id, message):
        if not message.strip():
            raise ValueError('A notification message is required.')
        with self.tasks._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            wake = db.execute('''SELECT w.id,a.family_id FROM automation_wakes w JOIN automations a ON a.id=w.automation_id
                JOIN family_tasks g ON g.id=a.goal_id WHERE w.run_goal_id=? AND a.enabled=1 AND w.version=a.version
                AND g.status!='paused' ''', (run_goal_id,)).fetchone()
            if not wake:
                raise ValueError('This automation is no longer active.')
            db.execute('''INSERT INTO automation_notifications(id,wake_id,family_id,message,created_at)
                VALUES (?,?,?,?,?) ON CONFLICT(wake_id) DO NOTHING''', (str(uuid4()),wake['id'],wake['family_id'],message.strip(),now()))
        return {'status':'delivered','channel':'in_app'}

    def notifications(self, family_id):
        with self.tasks._connect() as db:
            return [dict(row) for row in db.execute('''SELECT n.*,a.goal_id FROM automation_notifications n
                JOIN automation_wakes w ON w.id=n.wake_id JOIN automations a ON a.id=w.automation_id
                WHERE n.family_id=? ORDER BY n.created_at DESC LIMIT 50''', (family_id,)).fetchall()]
