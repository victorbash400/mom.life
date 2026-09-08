import json
from uuid import uuid4

from app.task_store import now


class ProviderEvents:
    """Persist exact event subscriptions and deduplicate provider deliveries."""
    def __init__(self,store):
        self.store=store
        with store._connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS provider_events (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL, plugin_id TEXT NOT NULL,
                    correlation TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL,
                    UNIQUE(family_id,plugin_id,id)
                );
                CREATE TABLE IF NOT EXISTS provider_waits (
                    id TEXT PRIMARY KEY, goal_id TEXT NOT NULL REFERENCES family_tasks(id) ON DELETE CASCADE,
                    assignment_id TEXT NOT NULL REFERENCES goal_assignments(id) ON DELETE CASCADE,
                    family_id TEXT NOT NULL, plugin_id TEXT NOT NULL, correlation TEXT NOT NULL,
                    state TEXT NOT NULL, created_at TEXT NOT NULL
                );
            ''')

    def wait(self,family_id,goal_id,assignment_id,plugin_id,correlation):
        if not correlation.strip():
            raise ValueError('An exact sender or provider correlation is required.')
        with self.store._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT a.id FROM goal_assignments a JOIN family_tasks g ON g.id=a.goal_id WHERE a.id=? AND g.id=? AND g.family_id=?',(assignment_id,goal_id,family_id)).fetchone()
            if not row:
                raise ValueError('Assignment does not belong to this family goal.')
            if plugin_id not in self.store.installed_plugins(family_id):
                raise ValueError('Install the event provider first.')
            db.execute("UPDATE provider_waits SET state='superseded' WHERE assignment_id=? AND state='waiting'",(assignment_id,))
            db.execute('INSERT INTO provider_waits VALUES (?,?,?,?,?,?,?,?)',(str(uuid4()),goal_id,assignment_id,family_id,plugin_id,correlation,'waiting',now()))

    def receive(self,family_id,plugin_id,event_id,correlation,payload):
        return self.receive_with_status(family_id,plugin_id,event_id,correlation,payload)['goal_ids']

    def receive_with_status(self,family_id,plugin_id,event_id,correlation,payload):
        with self.store._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing=db.execute('SELECT id FROM provider_events WHERE id=?',(event_id,)).fetchone()
            if existing:
                return {'goal_ids': [], 'matched': False, 'duplicate': True}
            db.execute('INSERT INTO provider_events VALUES (?,?,?,?,?,?)',(event_id,family_id,plugin_id,correlation,json.dumps(payload),now()))
            waits=db.execute("SELECT w.*,g.status AS goal_status FROM provider_waits w JOIN family_tasks g ON g.id=w.goal_id JOIN goal_assignments a ON a.id=w.assignment_id WHERE w.family_id=? AND w.plugin_id=? AND w.correlation=? AND w.state='waiting' AND g.status IN ('active','paused') AND a.status IN ('running','blocked')",(family_id,plugin_id,correlation)).fetchall()
            goals=[]
            for wait in waits:
                db.execute("UPDATE provider_waits SET state='received' WHERE id=?",(wait['id'],))
                db.execute("UPDATE goal_assignments SET status='queued',phase='queued' WHERE id=? AND status='blocked'",(wait['assignment_id'],))
                if wait['goal_status'] == 'active':
                    db.execute("UPDATE family_tasks SET run_state='queued' WHERE id=?",(wait['goal_id'],))
                db.execute('INSERT INTO goal_activities VALUES (?,?,?,?,?,?)',(str(uuid4()),wait['goal_id'],'provider_event','Received the awaited provider event',json.dumps({'plugin_id':plugin_id,'event_id':event_id,'payload':payload}),now()))
                if wait['goal_status'] == 'active':
                    goals.append(wait['goal_id'])
            return {'goal_ids': list(dict.fromkeys(goals)), 'matched': bool(waits), 'duplicate': False}
