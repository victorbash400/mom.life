import asyncio
import logging

from app.automation_scheduler import AutomationScheduler, validate_trigger
from app.automation_store import AutomationStore
from app.event_stream import family_events
from app.runtime_lock import acquire, acquire_wait, release


logger = logging.getLogger(__name__)


class AutomationManager:
    def __init__(self, tasks, goals, scheduler=None):
        self.tasks = tasks
        self.goals = goals
        goals._automation_manager = self
        self.store = AutomationStore(tasks)
        self.scheduler = scheduler or AutomationScheduler()
        self._runs = {}
        self._listener = None
        self._dirty = set()
        self.events_connected = False

    async def create(self, family_id, goal_id, instruction, trigger, schedule='', timezone='UTC'):
        if not instruction.strip():
            raise ValueError('Describe what to check and when to act.')
        validate_trigger(trigger,schedule,timezone)
        if trigger != 'time':
            item = await asyncio.to_thread(self.store.create,family_id,goal_id,instruction.strip(),trigger,schedule,timezone,True,'ready')
            self.publish(family_id)
            return item
        item = await asyncio.to_thread(self.store.create,family_id,goal_id,instruction.strip(),trigger,schedule,timezone)
        return await self.update(family_id,item['id'],enabled=True)

    async def update(self, family_id, identity, **changes):
        current = await asyncio.to_thread(self.store.get,family_id,identity)
        if current and current['trigger'] != 'time':
            return await self._update_event(family_id,identity,current,changes)
        lease = await asyncio.to_thread(acquire_wait,self.tasks.path,'automation:'+identity)
        try:
            return await self._update(family_id,identity,**changes)
        finally:
            release(lease)

    async def _update_event(self, family_id, identity, current, changes):
        proposed = {**current,**changes,'version':current['version']+1}
        if not proposed['instruction'].strip():
            raise ValueError('Describe what to check and when to act.')
        if proposed['enabled']:
            validate_trigger(proposed['trigger'],proposed['schedule'],proposed['timezone'])
        with self.tasks._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            changed = db.execute('''UPDATE automations SET enabled=?,version=?,instruction=?,schedule=?,timezone=?,
                scheduler_state='ready',failure='' WHERE id=? AND family_id=? AND version=?''',
                (int(proposed['enabled']),proposed['version'],proposed['instruction'],proposed['schedule'],proposed['timezone'],
                 identity,family_id,current['version'])).rowcount
            if not changed:
                raise ValueError('Automation changed. Read it again before updating.')
            rows = db.execute('SELECT run_goal_id FROM automation_wakes WHERE automation_id=? AND run_goal_id IS NOT NULL', (identity,)).fetchall()
            db.execute("UPDATE automation_wakes SET state='cancelled' WHERE automation_id=? AND state IN ('pending','running','blocked')", (identity,))
            item = self.store.get(family_id,identity,db)
        for row in rows:
            await self.goals.stop(row['run_goal_id'])
        self.publish(family_id)
        return item

    async def _update(self, family_id, identity, **changes):
        item = self.store.get(family_id,identity)
        if not item:
            raise ValueError('Automation not found.')
        proposed = {**item,**changes,'version':item['version']+1}
        if not proposed['instruction'].strip():
            raise ValueError('Describe what to check and when to act.')
        validate_trigger(proposed['trigger'],proposed['schedule'],proposed['timezone']) if proposed['enabled'] else None
        # Invalidate old deliveries before modifying AWS. Failure leaves the rule disabled and visible.
        with self.tasks._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            changed = db.execute('''UPDATE automations SET enabled=0,version=?,instruction=?,schedule=?,timezone=?,
                scheduler_state='pending',failure='' WHERE id=? AND family_id=? AND version=?''',
                (proposed['version'],proposed['instruction'],proposed['schedule'],proposed['timezone'],identity,family_id,item['version'])).rowcount
            if not changed:
                raise ValueError('Automation changed. Read it again before updating.')
            db.execute("UPDATE automation_wakes SET state='cancelled' WHERE automation_id=? AND state IN ('pending','running','blocked')", (identity,))
        await self._stop_runs(identity)
        try:
            await asyncio.to_thread(self.scheduler.save,proposed)
        except Exception as error:
            with self.tasks._connect() as db:
                db.execute("UPDATE automations SET scheduler_state='error',failure=? WHERE id=? AND version=?", (str(error),identity,proposed['version']))
            self.publish(family_id)
            return self.store.get(family_id,identity)
        with self.tasks._connect() as db:
            db.execute("UPDATE automations SET enabled=?,scheduler_state='ready' WHERE id=? AND version=?",
                       (int(proposed['enabled']),identity,proposed['version']))
        self.publish(family_id)
        return self.store.get(family_id,identity)

    async def delete(self, family_id, identity):
        current = await asyncio.to_thread(self.store.get,family_id,identity)
        if current and current['trigger'] != 'time':
            return await self._delete_event(family_id,identity,current)
        lease = await asyncio.to_thread(acquire_wait,self.tasks.path,'automation:'+identity)
        try:
            await self._delete(family_id,identity)
        finally:
            release(lease)

    async def _delete_event(self, family_id, identity, current):
        with self.tasks._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            changed = db.execute('UPDATE automations SET enabled=0,version=version+1 WHERE id=? AND family_id=? AND version=?',
                                 (identity,family_id,current['version'])).rowcount
            if not changed:
                raise ValueError('Automation changed. Read it again before deleting.')
            rows = db.execute('SELECT run_goal_id FROM automation_wakes WHERE automation_id=? AND run_goal_id IS NOT NULL', (identity,)).fetchall()
            db.execute('DELETE FROM automations WHERE id=? AND family_id=?', (identity,family_id))
        for row in rows:
            await self.goals.stop(row['run_goal_id'])
        self.publish(family_id)

    async def _delete(self, family_id, identity):
        item = self.store.get(family_id,identity)
        if not item:
            raise ValueError('Automation not found.')
        # Disable first so even an in-flight AWS delivery cannot create work.
        with self.tasks._connect() as db:
            db.execute('UPDATE automations SET enabled=0,version=version+1 WHERE id=? AND family_id=?', (identity,family_id))
        await self._stop_runs(identity)
        await asyncio.to_thread(self.scheduler.delete,item)
        with self.tasks._connect() as db:
            db.execute('DELETE FROM automations WHERE id=? AND family_id=?', (identity,family_id))
        self.publish(family_id)

    async def _stop_runs(self, identity):
        with self.tasks._connect() as db:
            rows = db.execute('SELECT run_goal_id FROM automation_wakes WHERE automation_id=? AND run_goal_id IS NOT NULL', (identity,)).fetchall()
        for row in rows:
            await self.goals.stop(row['run_goal_id'])

    def kick(self, family_id, goal_id):
        current = self._runs.get(goal_id)
        if current and not current.done():
            self._dirty.add(goal_id)
            return
        run = asyncio.create_task(self._run(family_id,goal_id),name=f'mom-life-automation-{goal_id}')
        self._runs[goal_id] = run
        def finished(done):
            if self._runs.get(goal_id) is done:
                self._runs.pop(goal_id,None)
                if goal_id in self._dirty:
                    self._dirty.discard(goal_id)
                    self.kick(family_id,goal_id)
        run.add_done_callback(finished)

    async def recover(self):
        with self.tasks._connect() as db:
            parents = db.execute("""SELECT DISTINCT g.id,g.family_id FROM family_tasks g
                JOIN automations a ON a.goal_id=g.id WHERE a.enabled=1 AND g.status='active'
                AND g.run_state IN ('queued','planning','running')""").fetchall()
        for parent in parents:
            await self.goals.start(parent['family_id'],parent['id'])
        for item in await asyncio.to_thread(self.store.pending_goals):
            self.kick(item['family_id'],item['goal_id'])

    async def _run(self, family_id, goal_id):
        # An existing task finishes its current checkpoint/run before another check starts.
        await self.goals.wait(goal_id)
        lease = await asyncio.to_thread(acquire,self.tasks.path,goal_id)
        if lease is None:
            return  # Owner completion emits a database notification and retries the saved inbox.
        try:
            while True:
                parent = await asyncio.to_thread(self.tasks.get,family_id,goal_id)
                if not parent or parent['status'] == 'paused':
                    return
                wake = await asyncio.to_thread(self.store.next_wake,family_id,goal_id)
                if not wake:
                    return
                run_id = await asyncio.to_thread(self.store.begin,wake,parent)
                if not run_id:
                    continue
                run = await asyncio.to_thread(self.tasks.get,family_id,run_id)
                if run['run_state'] == 'blocked':
                    return
                if run['status'] != 'completed' and run['run_state'] != 'failed':
                    # Restart recovery may have paused an interrupted run; reuse its assignment ledger.
                    await asyncio.to_thread(self.tasks.update,run_id,'active')
                    await self.goals.start(family_id,run_id,automation_check=True)
                    await self.goals.wait(run_id)
                    run = await asyncio.to_thread(self.tasks.get,family_id,run_id)
                    if run['run_state'] in {'queued','planning','running'}:
                        return
                state = await asyncio.to_thread(self.store.finish,wake,run)
                self.tasks.add_activity(goal_id,'automation_checked',run['report'] or run['current_step'],
                                        {'automation_id':wake['automation_id'],'run_goal_id':run_id,'state':state})
                self.publish(family_id)
                if state == 'blocked':
                    return
        except asyncio.CancelledError:
            raise
        except Exception as error:
            with self.tasks._connect() as db:
                db.execute("UPDATE automations SET failure=? WHERE family_id=? AND goal_id=?", (str(error),family_id,goal_id))
            self.publish(family_id)
            logger.exception('Automation worker failed for task %s',goal_id)
        finally:
            release(lease)

    async def listen(self):
        """LISTEN is a blocking database event subscription, not a periodic query."""
        import psycopg
        from app.config import get_settings
        try:
            async with await psycopg.AsyncConnection.connect(get_settings().database_url,autocommit=True) as db:
                await db.execute('LISTEN mom_life_automations')
                self.events_connected = True
                await self.recover()  # Subscribe first, then drain: no startup delivery gap.
                async for notification in db.notifies():
                    await self.recover()
                    with self.tasks._connect() as connection:
                        parent = connection.execute('SELECT family_id FROM family_tasks WHERE id=?', (notification.payload,)).fetchone()
                    if parent:
                        self.publish(parent['family_id'])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Automation database subscription disconnected; restart recovery remains available')
        finally:
            self.events_connected = False

    def start_listener(self):
        self._listener = asyncio.create_task(self.listen(),name='mom-life-automation-events')

    async def shutdown(self):
        running = [*self._runs.values(), *([self._listener] if self._listener else [])]
        self._dirty.clear()
        for run in running:
            run.cancel()
        await asyncio.gather(*running,return_exceptions=True)

    @staticmethod
    def publish(family_id):
        family_events.publish(family_id,{'type':'automations_changed'})
        family_events.publish(family_id,{'type':'goals_changed'})
