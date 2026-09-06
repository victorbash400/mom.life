"""Exercise the real planner ledger, worker tools, approval and resumed completion."""
import asyncio
from types import SimpleNamespace

from agents.goal_planner import AssignmentPlan, GoalPlan
from app.goal_tasks import GoalTaskManager
from app.task_store import TaskStore


def test_goal_to_approval_to_verified_result(tmp_path,monkeypatch):
    from app import goal_tasks
    from agents import goal_worker
    store=TaskStore(tmp_path/'flow.db')
    goal=store.create('family','child','Prepare a school-trip draft')
    store.install_plugin('family','microsoft-family')
    skill=SimpleNamespace(name='Draft preparation',description='Prepare a message',instructions='Create the requested draft.',required_plugin_ids=['microsoft-family'])
    skill_id=store.save_skill('family',skill)
    async def plan(*args,**kwargs):
        return GoalPlan(operations=[AssignmentPlan(action='create',key='draft',title='Prepare draft',instruction='Create the requested Outlook draft.',expected_outputs=['Saved draft'],skill_ids=[skill_id])])
    monkeypatch.setattr(goal_tasks,'plan_goal',plan)
    calls=[]
    class Plugins:
        def __init__(self,*args):
            self.loaded={}
        async def load(self,identity):
            self.loaded[identity]=[{'name':'create_draft','requires_approval':True}]
            return self.loaded[identity]
        async def call(self,identity,name,arguments,call_id):
            calls.append(arguments)
            return {'status':'success','data':{'id':'draft-proof-1','isDraft':True}}
        async def close(self):
            pass
    monkeypatch.setattr(goal_tasks,'PluginToolSession',Plugins)
    class Agent:
        def __init__(self,**kwargs):
            self.tools={item.tool_name:item for item in kwargs['tools']}
        async def stream_async(self,prompt):
            await self.tools['load_goal_tools'](['microsoft-family'])
            yield {}
            result=await self.tools['call_plugin']('microsoft-family','create_draft',{'subject':'School trip','body':'Please review supplies.'})
            yield {}
            if result['status']=='success':
                self.tools['complete_assignment']('Draft saved','Observed draft ID draft-proof-1',[{'name':'Saved draft','evidence':'Outlook returned draft-proof-1 with isDraft=true'}])
                yield {}
    monkeypatch.setattr(goal_worker,'Agent',Agent)
    monkeypatch.setattr(goal_worker,'BedrockModel',lambda **kwargs:None)
    async def run():
        manager=GoalTaskManager(store)
        await manager._orchestrate('family',goal['id'])
        blocked=store.get('family',goal['id'])
        assert blocked['run_state']=='blocked'
        assert calls==[]
        question=blocked['questions'][0]
        assert question['action']['arguments']['subject']=='School trip'
        assignment_id=blocked['assignments'][0]['id']
        store.answer_question('family',goal['id'],question['id'],'Approved',True)
        await manager._orchestrate('family',goal['id'])
        final=store.get('family',goal['id'])
        assert final['status']=='completed'
        assert final['assignments'][0]['id']==assignment_id
        assert len(calls)==1
        assert final['questions'][0]['state']=='consumed'
        assert any(event['kind']=='tool_result' for event in final['activities'])
        assert final['assignments'][0]['evidence']['outputs'][0]['name']=='Saved draft'
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
