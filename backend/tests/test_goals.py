import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agents.goal_planner import AssignmentPlan, GoalPlan
from app.task_store import TaskStore
from app.goal_tasks import GoalTaskManager


@pytest.fixture
def board(tmp_path):
    store = TaskStore(tmp_path/'goals.sqlite3')
    goal = store.create('family','child','Prepare a school trip')
    return store,goal['id']


def operation(**changes):
    return AssignmentPlan(**{'action':'create','key':'prepare','title':'Prepare supplies','instruction':'Prepare a supplies list','expected_outputs':['Supplies list'],**changes})


def test_plan_is_atomic_and_rejects_cross_goal_reference(board):
    store,goal = board
    with pytest.raises(ValueError):
        store.apply_plan('family',goal,[operation(),operation(action='cancel',task_id='foreign')])
    assert store.assignments(goal) == []


def test_plan_preserves_retry_identity_and_completed_evidence(board):
    store,goal = board
    store.apply_plan('family',goal,[operation()])
    identity = store.assignments(goal)[0]['id']
    store.set_assignment(identity,status='failed',report='Missing date')
    store.apply_plan('family',goal,[operation(action='retry',task_id=identity,instruction='Use confirmed Friday date')])
    assert len(store.assignments(goal)) == 1
    assert store.assignment(identity)['instruction'] == 'Use confirmed Friday date'
    store.set_assignment(identity,status='completed',evidence={'proof':'saved'})
    with pytest.raises(ValueError):
        store.apply_plan('family',goal,[operation(action='update',task_id=identity)])
    assert store.assignment(identity)['evidence'] == {'proof':'saved'}


def test_dependencies_and_duplicate_outcomes(board):
    store,goal = board
    store.apply_plan('family',goal,[operation(),operation(key='pack',title='Pack',depends_on=['prepare'])])
    first,second = store.assignments(goal)
    assert second['depends_on'] == [first['id']]
    with pytest.raises(ValueError):
        store.apply_plan('family',goal,[operation()])


def test_answer_is_scoped_and_approval_is_exact_and_once(board):
    store,goal = board
    store.apply_plan('family',goal,[operation()])
    identity = store.assignments(goal)[0]['id']
    action = {'plugin_id':'todoist','name':'create','arguments':{'title':'Shoes'}}
    question = store.question(goal,identity,'Approve?',action=action)
    with pytest.raises(ValueError):
        store.answer_question('other',goal,question,'yes',True)
    store.answer_question('family',goal,question,'yes',True)
    assert not store.consume_approval(identity,{**action,'name':'delete'})
    assert store.consume_approval(identity,action)
    assert not store.consume_approval(identity,action)
    assert store.questions(goal)[0]['state'] == 'consumed'


def test_recovery_pauses_without_destroying_evidence(board):
    store,goal = board
    store.apply_plan('family',goal,[operation()])
    identity = store.assignments(goal)[0]['id']
    store.set_assignment(identity,status='running',report='Already prepared')
    store.recover()
    assert store.get('family',goal)['status']=='paused'
    assert store.assignment(identity)['status']=='queued'
    assert store.assignment(identity)['report']=='Already prepared'


def test_reopening_store_does_not_interrupt_live_work(board):
    store,goal = board
    store.set_goal_state(goal,run_state='running')
    reopened = TaskStore(store.path)
    assert reopened.get('family',goal)['run_state']=='running'


def test_manager_plans_runs_and_completes(board,monkeypatch):
    store,goal = board
    from app import goal_tasks
    async def planner(*args,**kwargs):
        return GoalPlan(operations=[operation()])
    async def worker(prompt,plugins,progress,outputs,*args):
        progress('List prepared',90,'Verify quantities')
        return {'status':'completed','summary':'Prepared','evidence':'List text','outputs':[{'name':'Supplies list','evidence':'Water, lunch'}]}
    monkeypatch.setattr(goal_tasks,'plan_goal',planner)
    monkeypatch.setattr(goal_tasks,'run_worker',worker)
    async def run():
        manager = GoalTaskManager(store)
        assert await manager.start('family',goal)
        assert not await manager.start('family',goal)
        await manager._workers[goal]
    asyncio.run(run())
    result = store.get('family',goal)
    assert result['status']=='completed'
    assert result['assignments'][0]['evidence']['outputs'][0]['evidence']=='Water, lunch'


def test_manager_failure_is_visible_and_requires_retry(board,monkeypatch):
    store,goal = board
    store.apply_plan('family',goal,[operation()])
    from app import goal_tasks
    async def fail(*args):
        raise RuntimeError('Provider denied access')
    monkeypatch.setattr(goal_tasks,'run_worker',fail)
    asyncio.run(GoalTaskManager(store)._orchestrate('family',goal))
    result = store.get('family',goal)
    assert result['run_state']=='failed'
    assert result['assignments'][0]['status']=='failed'
    assert result['current_step']=='Provider denied access'


def test_worker_terminal_and_completion_requirements(board,monkeypatch):
    from agents import goal_worker
    store,goal = board
    store.apply_plan('family',goal,[operation()])
    identity = store.assignments(goal)[0]['id']
    captured = {}
    class FakeAgent:
        def __init__(self,**kwargs):
            captured.update(kwargs)
        async def stream_async(self,prompt):
            methods = {t.tool_name:t for t in captured['tools']}
            rejected = methods['complete_assignment']('Done','Evidence',[])
            assert rejected['status']=='failed'
            methods['ask_mom']('Which school?')
            event = SimpleNamespace(cancel_tool=False)
            captured['hooks'][0].before(event)
            assert event.cancel_tool
            yield {}
    monkeypatch.setattr(goal_worker,'Agent',FakeAgent)
    monkeypatch.setattr(goal_worker,'BedrockModel',lambda **kwargs:None)
    result = asyncio.run(goal_worker.run_worker('{}',SimpleNamespace(),lambda *args:None,['Supplies list'],store,goal,identity))
    assert result['status']=='blocked'
    assert store.questions(goal)[0]['question']=='Which school?'


def test_blocked_answer_is_in_resumed_worker_context(board,monkeypatch):
    from app import goal_tasks
    store,goal = board
    store.apply_plan('family',goal,[operation()])
    identity = store.assignments(goal)[0]['id']
    question = store.question(goal,identity,'Which school?')
    store.set_assignment(identity,status='blocked')
    store.answer_question('family',goal,question,'Oak school')
    async def worker(prompt,*args):
        assert json.loads(prompt)['mom_answers'][0]['answer']=='Oak school'
        return {'status':'completed','summary':'Prepared','evidence':'Observed','outputs':[{'name':'Supplies list','evidence':'Lunch'}]}
    monkeypatch.setattr(goal_tasks,'run_worker',worker)
    asyncio.run(GoalTaskManager(store)._orchestrate('family',goal))
    assert store.get('family',goal)['status']=='completed'


def test_api_rejects_other_family_and_manual_completion(board,monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    store,goal = board
    monkeypatch.setattr(main,'task_store',store)
    monkeypatch.setattr(main,'goal_tasks',AsyncMock())
    client = TestClient(main.app)
    assert client.patch(f'/api/tasks/{goal}?family_id=other',json={'status':'paused'}).status_code==404
    assert client.delete(f'/api/tasks/{goal}?family_id=other').status_code==404
    assert client.patch(f'/api/tasks/{goal}?family_id=family',json={'status':'completed'}).status_code==409


def test_slow_event_subscriber_receives_invalidation():
    from app.event_stream import FamilyEvents
    events=FamilyEvents()
    queue=events.subscribe('family')
    for i in range(100):
        events.publish('family',{'type':'goals_changed','goal_id':str(i)})
    assert queue.qsize()==32
    assert any(queue.get_nowait()['type']=='goals_changed' for _ in range(32))
    assert not events.subscribe('other').qsize()


def test_revision_invalidates_unused_approval(board):
    store,goal=board
    store.apply_plan('family',goal,[operation()])
    identity=store.assignments(goal)[0]['id']
    action={'plugin_id':'todoist','name':'create','arguments':{}}
    question=store.question(goal,identity,'Approve?',action=action)
    store.answer_question('family',goal,question,'Yes',True)
    store.apply_plan('family',goal,[operation(action='update',task_id=identity,instruction='Prepare a different list')])
    assert not store.consume_approval(identity,action)
    assert store.questions(goal)[0]['state']=='superseded'


def test_runtime_lock_prevents_duplicate_manager_and_recovery(board,monkeypatch):
    store,goal=board
    from app import goal_tasks
    gate=asyncio.Event()
    async def work(*args):
        await gate.wait()
    async def run():
        manager=GoalTaskManager(store)
        monkeypatch.setattr(manager,'_orchestrate',work)
        assert await manager.start('family',goal)
        assert not await GoalTaskManager(store).start('family',goal)
        store.recover()
        assert store.get('family',goal)['status']=='active'
        await manager.stop(goal)
    asyncio.run(run())


def test_approval_cannot_be_consumed_concurrently(board):
    from concurrent.futures import ThreadPoolExecutor
    store,goal=board
    store.apply_plan('family',goal,[operation()])
    identity=store.assignments(goal)[0]['id']
    action={'plugin_id':'todoist','name':'create','arguments':{}}
    question=store.question(goal,identity,'Approve?',action=action)
    store.answer_question('family',goal,question,'Yes',True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(lambda _:store.consume_approval(identity,action),range(8)))
    assert results.count(True)==1


def test_dependency_revision_rejects_cycle_atomically(board):
    store,goal=board
    store.apply_plan('family',goal,[operation(),operation(key='pack',title='Pack',depends_on=['prepare'])])
    first,second=store.assignments(goal)
    with pytest.raises(ValueError,match='cycle'):
        store.apply_plan('family',goal,[operation(action='update',task_id=first['id'],depends_on=[second['id']])])
    assert store.assignment(first['id'])['depends_on']==[]


def test_cancelled_dependency_requires_coherent_revision(board):
    store,goal=board
    store.apply_plan('family',goal,[operation(),operation(key='pack',title='Pack',depends_on=['prepare'])])
    first,second=store.assignments(goal)
    with pytest.raises(ValueError,match='cancelled'):
        store.apply_plan('family',goal,[operation(action='cancel',task_id=first['id'])])
    assert store.assignment(first['id'])['status']=='queued'
    store.apply_plan('family',goal,[operation(action='cancel',task_id=first['id']),operation(action='update',task_id=second['id'],depends_on=[])])
    assert store.assignment(second['id'])['depends_on']==[]


def test_stale_answer_does_not_stop_active_work(board,monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    store,goal=board
    manager=AsyncMock()
    monkeypatch.setattr(main,'task_store',store)
    monkeypatch.setattr(main,'goal_tasks',manager)
    response=TestClient(main.app).post(f'/api/tasks/{goal}/questions/missing?family_id=family',json={'answer':'Yes','approved':True})
    assert response.status_code==400
    manager.stop.assert_not_awaited()
    assert store.get('family',goal)['status']=='active'
