import asyncio
import json
from datetime import datetime, UTC, timedelta
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app import main
from app.automation_manager import AutomationManager
from app.automation_scheduler import AutomationScheduler
from app.automation_store import AutomationStore
from app.task_store import TaskStore

class Scheduler:
    def __init__(self):
        self.saved = []
        self.deleted = []
        self.failure = ''
    def save(self,item):
        if self.failure: raise RuntimeError(self.failure)
        self.saved.append(dict(item))
    def delete(self,item): self.deleted.append(item['id'])

class Goals:
    def __init__(self,tasks):
        self.tasks = tasks
        self._workers = {}
        self.started = []
        self.block = False
    async def wait(self,identity):
        if identity in self._workers: await asyncio.shield(self._workers[identity])
    async def start(self,family_id,identity,**options):
        self.started.append(identity)
        async def run():
            self.tasks.set_goal_state(identity,status='active' if self.block else 'completed',run_state='blocked' if self.block else 'completed',report='Sleep checked; no action needed.')
        self._workers[identity] = asyncio.create_task(run())
        return True
    async def stop(self,identity):
        current = self._workers.get(identity)
        if current and not current.done():
            current.cancel()
            await asyncio.gather(current,return_exceptions=True)

@pytest.fixture
def system(tmp_path):
    tasks = TaskStore(tmp_path/'tasks.sqlite3')
    parent = tasks.create('family','child','Monitor sleep and notify if the requested condition occurs.')
    tasks.set_goal_state(parent['id'],run_state='waiting')
    goals,scheduler = Goals(tasks),Scheduler()
    manager = AutomationManager(tasks,goals,scheduler)
    return tasks,parent,goals,scheduler,manager

def create(system,trigger='health',schedule=''):
    tasks,parent,goals,scheduler,manager = system
    return asyncio.run(manager.create('family',parent['id'],'Check sleep and notify only if necessary.',trigger,schedule))

def drain(manager):
    async def run():
        await manager.recover()
        await asyncio.gather(*manager._runs.values())
    asyncio.run(run())

def test_event_scope_and_deduplication(system):
    tasks,parent,goals,scheduler,manager = system
    item = create(system)
    assert manager.store.enqueue_event('family',{'other'},'health','one',{}) == set()
    assert manager.store.enqueue_event('other',{'child'},'health','one',{}) == set()
    assert manager.store.enqueue_event('family',{'child'},'health','one',{'value':8}) == {parent['id']}
    assert manager.store.enqueue_event('family',{'child'},'health','one',{}) == set()
    assert json.loads(manager.store.next_wake('family',parent['id'])['context']) == {'value':8}

def test_restart_recovery_and_context(system):
    tasks,parent,goals,scheduler,manager = system
    item = create(system)
    manager.store.enqueue(item['id'],item['version'],'event',{'sample_count':3})
    recovered = AutomationManager(TaskStore(tasks.database),goals,scheduler)
    drain(recovered)
    checked = recovered.store.get('family',item['id'])
    assert checked['enabled'] and checked['last_checked_at']
    assert checked['last_result'] == 'Sleep checked; no action needed.'
    run = tasks.get('family',goals.started[0])
    assert 'sample_count' in run['text'] and 'last_checked_at' in run['text'] and parent['text'] in run['text']
    assert len(run['assignments']) == 1
    assert run['assignments'][0]['expected_outputs'] == ['Automation check result']

def test_interrupted_run_reuses_existing_task(system):
    tasks,parent,goals,scheduler,manager = system
    item = create(system)
    manager.store.enqueue(item['id'],item['version'],'event',{})
    run_id = manager.store.begin(manager.store.next_wake('family',parent['id']),parent)
    tasks.set_goal_state(run_id,status='paused',run_state='paused')
    drain(AutomationManager(TaskStore(tasks.database),goals,scheduler))
    assert goals.started == [run_id]
    assert manager.store.next_wake('family',parent['id']) is None

def test_busy_parent_serializes_multiple_wakes(system):
    tasks,parent,goals,scheduler,manager = system
    item = create(system)
    async def run():
        barrier = asyncio.Event()
        goals._workers[parent['id']] = asyncio.create_task(barrier.wait())
        manager.store.enqueue(item['id'],item['version'],'one',{})
        manager.store.enqueue(item['id'],item['version'],'two',{})
        manager.kick('family',parent['id'])
        await asyncio.sleep(0)
        assert not goals.started
        barrier.set()
        await asyncio.gather(*manager._runs.values())
    asyncio.run(run())
    assert len(goals.started) == 2 and len(set(goals.started)) == 2

def test_pause_invalidates_deliveries_and_late_completion(system):
    tasks,parent,goals,scheduler,manager = system
    item = create(system)
    manager.store.enqueue(item['id'],item['version'],'one',{})
    wake = manager.store.next_wake('family',parent['id'])
    run_id = manager.store.begin(wake,parent)
    paused = asyncio.run(manager.update('family',item['id'],enabled=False))
    assert not paused['enabled']
    assert not manager.store.enqueue(item['id'],item['version'],'late',{})
    with pytest.raises(ValueError): manager.store.require_active_run(run_id)
    assert manager.store.finish(wake,{'status':'completed','report':'late','run_state':'completed','current_step':''}) == 'cancelled'
    assert not manager.store.get('family',item['id'])['last_checked_at']

def test_delete_keeps_provider_guard(system):
    tasks,parent,goals,scheduler,manager = system
    item = create(system)
    manager.store.enqueue(item['id'],item['version'],'event',{})
    run_id = manager.store.begin(manager.store.next_wake('family',parent['id']),parent)
    asyncio.run(manager.delete('family',item['id']))
    assert manager.store.list('family') == []
    assert not manager.store.enqueue(item['id'],item['version'],'late',{})
    with pytest.raises(ValueError): manager.store.require_active_run(run_id)

def test_notifications_deduplicate_and_scope(system):
    tasks,parent,goals,scheduler,manager = system
    item = create(system)
    manager.store.enqueue(item['id'],item['version'],'event',{})
    run_id = manager.store.begin(manager.store.next_wake('family',parent['id']),parent)
    assert manager.store.notify(run_id,'Sleep condition met.')['channel'] == 'in_app'
    manager.store.notify(run_id,'Repeated attempt')
    assert len(manager.store.notifications('family')) == 1
    assert manager.store.notifications('other') == []

def test_scheduler_failure_is_visible(system):
    tasks,parent,goals,scheduler,manager = system
    scheduler.failure = 'AWS access denied'
    item = create(system,'time','rate(1 minute)')
    assert not item['enabled'] and item['scheduler_state'] == 'error'
    assert item['failure'] == 'AWS access denied'

def test_aws_payload_version_and_precision():
    captured = []
    client = SimpleNamespace(create_schedule=lambda **args:captured.append(args))
    settings = SimpleNamespace(automation_target_arn='lambda',automation_role_arn='role',automation_dlq_arn='dlq',automation_schedule_group='mom-life')
    AutomationScheduler(settings,client).save({'id':'rule','version':3,'trigger':'time','schedule':'at(2026-09-12T12:00:30)','timezone':'Africa/Nairobi','enabled':True})
    target = captured[0]
    assert target['FlexibleTimeWindow'] == {'Mode':'OFF'} and target['ActionAfterCompletion'] == 'DELETE'
    assert json.loads(target['Target']['Input']) == {'automation_id':'rule','version':3,'scheduled_at':'<aws.scheduler.scheduled-time>'}
    assert target['Target']['DeadLetterConfig'] == {'Arn':'dlq'}

def test_api_ownership_and_hidden_internal_runs(system,auth_headers,monkeypatch):
    tasks,parent,goals,scheduler,manager = system
    monkeypatch.setattr(main,'task_store',tasks)
    monkeypatch.setattr(main,'goal_tasks',goals)
    monkeypatch.setattr(main,'automations',manager)
    client = TestClient(main.app)
    client.headers.update(auth_headers('family'))
    response = client.post('/api/automations',json={'goal_id':parent['id'],'instruction':'Watch sleep','trigger':'health'})
    assert response.status_code == 201
    item = response.json()
    manager.store.enqueue(item['id'],item['version'],'event',{})
    manager.store.begin(manager.store.next_wake('family',parent['id']),parent)
    assert [task['id'] for task in client.get('/api/tasks').json()] == [parent['id']]
    assert client.get(f"/api/automations/{item['id']}/runs").json()[0]['task']
    client.headers.update(auth_headers('other'))
    assert client.get('/api/automations').json()['automations'] == []
    assert client.delete(f"/api/automations/{item['id']}").status_code == 404

def test_real_30_second_wake_and_closed_backend_recovery(system):
    tasks,parent,goals,scheduler,manager = system
    target = datetime.now(UTC) + timedelta(seconds=30)
    item = create(system,'time',f"at({target.strftime('%Y-%m-%dT%H:%M:%S')})")
    async def run():
        delivered = asyncio.Event()
        def fire():
            AutomationStore(TaskStore(tasks.database)).enqueue(item['id'],item['version'],target.isoformat(),{'scheduled_at':target.isoformat()})
            delivered.set()
        asyncio.get_running_loop().call_later(30,fire)
        await asyncio.wait_for(delivered.wait(),35)
        recovered = AutomationManager(TaskStore(tasks.database),goals,scheduler)
        await recovered.recover()
        await asyncio.gather(*recovered._runs.values())
    asyncio.run(run())
    checked = manager.store.get('family',item['id'])
    assert checked['last_checked_at']
    assert not checked['enabled'] and checked['scheduler_state'] == 'completed'


def test_restart_resumes_interrupted_automation_parent(system):
    tasks,parent,goals,scheduler,manager = system
    item = create(system)
    tasks.set_goal_state(parent['id'],status='active',run_state='running')
    manager.store.enqueue(item['id'],item['version'],'event',{})
    tasks.recover()
    recovered_parent = tasks.get('family',parent['id'])
    assert recovered_parent['status'] == 'active' and recovered_parent['run_state'] == 'queued'
    drain(manager)
    assert goals.started[0] == parent['id']
    assert manager.store.get('family',item['id'])['last_checked_at']


def test_incoming_wake_is_atomic_with_saved_information(system):
    tasks,parent,goals,scheduler,manager = system
    item = create(system,'incoming')
    incoming,created = tasks.receive_incoming('family','school','report-one',content='Subject result updated.',payload={'child_id':'child'})
    assert created
    wake = manager.store.next_wake('family',parent['id'])
    assert json.loads(wake['context'])['incoming_id'] == incoming['id']
    assert not tasks.receive_incoming('family','school','report-one',content='Same receipt')[1]
    with tasks._connect() as db:
        assert db.execute('SELECT COUNT(*) FROM automation_wakes').fetchone()[0] == 1


def test_provider_or_question_resume_routes_through_parent_controller(system):
    from app.goal_tasks import GoalTaskManager
    tasks,parent,goals,scheduler,manager = system
    item = create(system)
    manager.store.enqueue(item['id'],item['version'],'event',{})
    run_id = manager.store.begin(manager.store.next_wake('family',parent['id']),parent)
    worker = GoalTaskManager(tasks)
    routed = []
    worker._automation_manager = SimpleNamespace(store=manager.store,kick=lambda family,goal:routed.append((family,goal)))
    assert asyncio.run(worker.start('family',run_id))
    assert routed == [('family',parent['id'])]
    assert not worker._workers


def test_failed_check_is_visible_and_preserved_for_next_wake(system):
    tasks,parent,goals,scheduler,manager = system
    item = create(system)
    manager.store.enqueue(item['id'],item['version'],'failed',{})
    wake = manager.store.next_wake('family',parent['id'])
    run_id = manager.store.begin(wake,parent)
    tasks.set_goal_state(run_id,run_state='failed',current_step='Provider access denied')
    assert manager.store.finish(wake,tasks.get('family',run_id)) == 'failed'
    checked = manager.store.get('family',item['id'])
    assert checked['enabled'] and checked['failure'] == 'Provider access denied'
    assert checked['last_checked_at'] and checked['last_result'] == checked['failure']
    manager.store.enqueue(item['id'],item['version'],'next',{})
    retry = manager.store.next_wake('family',parent['id'])
    assert retry['last_result'] == 'Provider access denied'
    next_id = manager.store.begin(retry,parent)
    tasks.set_goal_state(next_id,status='completed',run_state='completed',report='Check completed.')
    manager.store.finish(retry,tasks.get('family',next_id))
    assert manager.store.get('family',item['id'])['failure'] == ''


def test_wake_executes_with_parent_providers_and_baseline(system, monkeypatch):
    from app import goal_tasks
    from app.goal_tasks import GoalTaskManager

    tasks, parent, _, scheduler, _ = system
    tasks.set_goal_state(parent['id'], status='completed', plugin_ids=['fitbit', 'whatsapp'])
    baseline = tasks.create_assignment(parent['id'], {
        'title':'Sleep baseline', 'instruction':'Read the baseline',
        'expected_outputs':['Sleep baseline'], 'plugin_ids':['fitbit'],
    })
    tasks.set_assignment(baseline, status='completed', report='8.5 hours',
                         evidence={'outputs':[{'name':'Sleep baseline','evidence':'8.5 hours measured'}]})
    manager = AutomationManager(tasks, GoalTaskManager(tasks), scheduler)
    item = asyncio.run(manager.create('family', parent['id'], 'Compare sleep and send a WhatsApp if below 7 hours.', 'health'))
    seen = {}

    async def worker(prompt, plugins, *args, **kwargs):
        seen['providers'] = plugins.plugin_ids
        instruction = json.loads(prompt)['instruction']
        assert '8.5 hours measured' in instruction
        return {'status':'completed','summary':'Checked baseline','evidence':'Read provider receipt',
                'outputs':[{'name':'Automation check result','evidence':'Read provider receipt'}]}

    monkeypatch.setattr(goal_tasks, 'run_worker', worker)
    manager.store.enqueue(item['id'], item['version'], 'changed', {'child_id':'child'})
    drain(manager)
    assert seen['providers'] == ['fitbit', 'whatsapp']
    assert manager.store.get('family', item['id'])['last_result'] == 'Checked baseline'


def test_worker_automation_tool_links_current_task_without_internal_id(system, monkeypatch):
    from tools.automation_tools import automation_tools

    tasks, parent, _, _, manager = system
    monkeypatch.setattr(main, 'automations', manager)
    create_tool = next(tool for tool in automation_tools('family', parent['id']) if tool.tool_name == 'create_automation')
    receipt = asyncio.run(create_tool(instruction='Check changed sleep data.', trigger='health'))
    assert receipt['goal_id'] == parent['id'] and receipt['enabled']
    with pytest.raises(ValueError, match='assigned task'):
        asyncio.run(create_tool(instruction='Check', trigger='health', task_id='another-task'))
