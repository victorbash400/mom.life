"""Exercise the real planner ledger, worker tools, and verified completion."""
import asyncio
from types import SimpleNamespace

from agents.goal_planner import AssignmentPlan, GoalPlan
from app.goal_tasks import GoalTaskManager
from app.event_stream import family_events
from app.task_store import TaskStore


def test_goal_to_verified_result(tmp_path,monkeypatch):
    from app import goal_tasks
    from agents import goal_worker
    store=TaskStore(tmp_path/'flow.db')
    goal=store.create('family','child','Send a school-trip update')
    store.install_plugin('family','whatsapp')
    skill=SimpleNamespace(name='Family update',description='Send a message',instructions='Send the requested update.',required_plugin_ids=['whatsapp'])
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
        def cancel(self):
            pass
        async def invoke_async(self,prompt):
            await self.tools['update_progress']('Checked the school-trip request', 30, 'Prepare the update', 'checking')
            await self.tools['load_goal_tools'](['whatsapp'])
            result=await self.tools['call_plugin']('whatsapp','send_text',{'to':'254700000000','text':'Please review the school-trip supplies.'})
            if result['status']=='success':
                self.tools['complete_assignment']('Update sent','Observed provider message ID message-proof-1',[{'Sent message':'WhatsApp returned message-proof-1'}])
    monkeypatch.setattr(goal_worker,'Agent',Agent)
    monkeypatch.setattr(goal_worker,'BedrockModel',lambda **kwargs:None)
    async def run():
        queue = family_events.subscribe('family')
        other_queue = family_events.subscribe('other-family')
        manager=GoalTaskManager(store)
        await manager._orchestrate('family',goal['id'])
        final=store.get('family',goal['id'])
        assert final['status']=='completed'
        assert len(calls)==1
        updates = [item for item in final['activities'] if item['kind'] == 'worker_update']
        assert updates[0]['summary'] == 'Checked the school-trip request'
        assert updates[0]['evidence']['assignment_id'] == final['assignments'][0]['id']
        assert final['questions'] == []
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


def test_builtin_skill_changes_replace_removed_plugin_dependencies(tmp_path):
    store=TaskStore(tmp_path/'skills.db')
    original={'slug':'care','name':'Care','description':'Care','instructions':'Old','required_plugin_ids':['mychart']}
    current={**original,'instructions':'Current','required_plugin_ids':['google-workspace']}
    store.seed_skills('family',(original,))
    store.seed_skills('family',(current,))
    skill=store.skills('family')[0]
    assert skill['instructions']=='Current'
    assert skill['required_plugin_ids']==['google-workspace']


def test_planner_can_select_an_unconnected_skill_by_slug(tmp_path, monkeypatch):
    from app import goal_tasks

    store = TaskStore(tmp_path / 'skill-reference.db')
    goal = store.create('family', 'child', 'Complete the school trip permission form')

    async def plan(*args, **kwargs):
        skills = args[2]
        school_skill = next(skill for skill in skills if skill['slug'] == 'school-notice-follow-through')
        assert school_skill['available'] is True
        assert school_skill['connection_setup_required'] == ['google-workspace']
        return GoalPlan(operations=[AssignmentPlan(
            action='create',
            key='permission-form',
            title='Prepare the permission form',
            instruction='Prepare the school trip permission form and ask before submitting it.',
            expected_outputs=['Prepared permission form'],
            skill_ids=['school-notice-follow-through'],
        )])

    monkeypatch.setattr(goal_tasks, 'plan_goal', plan)
    assignments = asyncio.run(GoalTaskManager(store)._plan('family', goal))
    selected = assignments[0]['skill_ids'][0]
    assert selected != 'school-notice-follow-through'
    assert store.assignment(assignments[0]['id'])['skill_ids'] == [selected]
    assert store.get('family', goal['id'])['plugin_ids'] == ['google-workspace']
