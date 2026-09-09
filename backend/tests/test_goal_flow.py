"""Exercise the real planner ledger, worker tools, approval and resumed completion."""
import asyncio
from types import SimpleNamespace

from agents.goal_planner import AssignmentPlan, GoalPlan
from app.goal_tasks import GoalTaskManager
from app.event_stream import family_events
from app.task_store import TaskStore


def test_goal_to_approval_to_verified_result(tmp_path,monkeypatch):
    from app import goal_tasks
    from agents import goal_worker
    store=TaskStore(tmp_path/'flow.db')
    goal=store.create('family','child','Send a school-trip update')
    store.install_plugin('family','whatsapp')
    skill=SimpleNamespace(name='Family update',description='Send a message',instructions='Send the approved update.',required_plugin_ids=['whatsapp'])
    skill_id=store.save_skill('family',skill)
    async def plan(*args,**kwargs):
        return GoalPlan(operations=[AssignmentPlan(action='create',key='message',title='Send update',instruction='Send the requested WhatsApp update.',expected_outputs=['Sent message'],skill_ids=[skill_id])])
    monkeypatch.setattr(goal_tasks,'plan_goal',plan)
    calls=[]
    class Plugins:
        def __init__(self,*args):
            self.loaded={}
            self.family_id='family'
        async def load(self,identity):
            self.loaded[identity]=[{'name':'send_text','requires_approval':True}]
            return self.loaded[identity]
        async def call(self,identity,name,arguments,call_id):
            calls.append(arguments)
            return {'status':'success','data':{'messages':[{'id':'message-proof-1'}]}}
        async def close(self):
            pass
    monkeypatch.setattr(goal_tasks,'PluginToolSession',Plugins)
    class Agent:
        def __init__(self,**kwargs):
            self.tools={item.tool_name:item for item in kwargs['tools']}
        async def stream_async(self,prompt):
            await self.tools['update_progress']('Checked the school-trip request', 30, 'Prepare the update', 'checking')
            yield {}
            await self.tools['load_goal_tools'](['whatsapp'])
            yield {}
            result=await self.tools['call_plugin']('whatsapp','send_text',{'to':'254700000000','text':'Please review the school-trip supplies.'})
            yield {}
            if result['status']=='success':
                self.tools['complete_assignment']('Update sent','Observed provider message ID message-proof-1',[{'name':'Sent message','evidence':'WhatsApp returned message-proof-1'}])
                yield {}
    monkeypatch.setattr(goal_worker,'Agent',Agent)
    monkeypatch.setattr(goal_worker,'BedrockModel',lambda **kwargs:None)
    async def run():
        queue = family_events.subscribe('family')
        other_queue = family_events.subscribe('other-family')
        manager=GoalTaskManager(store)
        await manager._orchestrate('family',goal['id'])
        blocked=store.get('family',goal['id'])
        assert blocked['run_state']=='blocked'
        assert calls==[]
        updates = [item for item in blocked['activities'] if item['kind'] == 'worker_update']
        assert updates[0]['summary'] == 'Checked the school-trip request'
        assert updates[0]['evidence']['assignment_id'] == blocked['assignments'][0]['id']
        question=blocked['questions'][0]
        assert question['action']['arguments']['to']=='254700000000'
        assignment_id=blocked['assignments'][0]['id']
        store.answer_question('family',goal['id'],question['id'],'Approved',True)
        await manager._orchestrate('family',goal['id'])
        final=store.get('family',goal['id'])
        assert final['status']=='completed'
        assert final['assignments'][0]['id']==assignment_id
        assert len(calls)==1
        assert final['questions'][0]['state']=='consumed'
        assert any(event['kind']=='tool_result' for event in final['activities'])
        assert final['assignments'][0]['evidence']['outputs'][0]['name']=='Sent message'
        assert not queue.empty()
        assert other_queue.empty()
        assert TaskStore(store.path).get('family', goal['id'])['activities'] == final['activities']
        family_events.unsubscribe('family', queue)
        family_events.unsubscribe('other-family', other_queue)
    asyncio.run(run())


def test_board_scope_resolves_only_own_family_skills(tmp_path):
    store = TaskStore(tmp_path / 'scope.db')
    goal = store.create('family', 'child', 'Prepare draft')
    skill = SimpleNamespace(name='Mail', description='Draft mail', instructions='Prepare a draft.', required_plugin_ids=['google-workspace'])
    identity = store.save_skill('family', skill)
    other = store.save_skill('other-family', skill)
    store.create_assignment(goal['id'], {'title': 'Draft', 'instruction': 'Prepare it', 'skill_ids': [identity]})
    board = store.get('family', goal['id'])
    assignment = board['assignments'][0]
    assert [item['id'] for item in assignment['skills']] == [identity]
    assert other not in str(assignment)
    assert 'workspace.gmail' in assignment['permitted_namespaces']
    assert store.get('other-family', goal['id']) is None
