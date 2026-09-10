"""Exercise account/child/file ownership against the configured PostgreSQL database."""
from io import BytesIO
from uuid import uuid4
from fastapi.testclient import TestClient
from PIL import Image
from app import main, auth
from app.database import connect


def test_registration_children_and_folders_postgres():
    clients = [TestClient(main.app), TestClient(main.app)]
    families = []
    try:
        for client in clients:
            email = f'test-{uuid4()}@example.com'
            response = client.post('/api/auth/register', json={'name':'Test Parent','email':email,'password':'TestPassword!123'})
            assert response.json()['family_id']
            assert response.status_code == 201, response.text
            client.headers['Authorization'] = 'Bearer ' + response.json()['token']
            family = client.get('/api/family').json()
            families.append(family['id'])
            assert family['children'] == []
            assert family['parent']['name'] == 'Test Parent'
            assert client.post('/api/auth/register', json={'name':'Again','email':email,'password':'TestPassword!123'}).status_code == 409
            assert client.post('/api/auth/login', json={'email':email,'password':'TestPassword!123'}).status_code == 200
        client, other = clients
        parent_folder = client.post('/api/family/children/parent/folders',json={'name':'Family papers'})
        assert parent_folder.status_code == 201, parent_folder.text
        assert len(client.get('/api/family/children/parent/nodes').json()) == 1
        assert other.get('/api/family/children/parent/nodes').json() == []
        response = client.post('/api/family/children', json={'name':'A Child','birth_date':'2020-01-01'})
        assert response.status_code == 201, response.text
        identity = response.json()['id']
        root = f'/api/family/children/{identity}'
        assert other.get(root+'/nodes').status_code == 404
        assert client.patch(root,json={'name':'Updated','notifications':False}).status_code == 200
        assert client.get('/api/family').json()['children'][0]['notifications'] is False
        assert client.get(root+'/avatar').headers['content-type'].startswith('image/svg+xml')
        output=BytesIO(); Image.new('RGB',(12,12),'red').save(output,format='PNG')
        assert client.put(root+'/photo',files={'file':('photo.png',output.getvalue(),'image/png')}).status_code == 200
        assert client.get(root+'/photo').headers['content-type']=='image/jpeg'
        folder = client.post(root+'/folders',json={'name':'School'}).json()['id']
        nested = client.post(root+'/folders',json={'name':'Reports','parent_id':folder}).json()['id']
        assert client.post(root+'/folders',json={'name':'School'}).status_code == 409
        uploaded=client.post(root+'/files',data={'parent_id':nested},files={'file':('report.txt',b'Family report','text/plain')})
        assert uploaded.status_code == 201, uploaded.text
        file_id=uploaded.json()['id']
        assert client.get(root+f'/files/{file_id}').content == b'Family report'
        assert other.get(root+f'/files/{file_id}').status_code == 404
        assert len(client.get(root+'/nodes').json()) == 3
        assert client.delete(root+f'/nodes/{folder}').status_code == 204
        assert client.get(root+'/nodes').json() == []
        assert client.delete(root).status_code == 204
        assert client.get('/api/family').json()['children'] == []
    finally:
        with connect(auth.families.url) as db:
            for identity in families:
                db.execute('DELETE FROM auth_sessions WHERE family_id=?',(identity,))
                db.execute('DELETE FROM children WHERE family_id=?',(identity,))
                db.execute('DELETE FROM family_nodes WHERE family_id=?',(identity,))
                db.execute('DELETE FROM accounts WHERE family_id=?',(identity,))
                db.execute('DELETE FROM families WHERE id=?',(identity,))


def test_postgres_goal_ledger_and_session_precision():
    from app.task_store import TaskStore
    from app.config import get_settings
    from agents.goal_planner import AssignmentPlan
    from app.provider_events import ProviderEvents
    store = TaskStore(get_settings().database_url)
    family = 'test-' + str(uuid4())
    goal = store.create(family,'all','Verify PostgreSQL ledger')
    try:
        store.apply_plan(family,goal['id'],[AssignmentPlan(action='create',key='one',title='One',instruction='Prepare output',expected_outputs=['Output'])])
        task = store.assignments(goal['id'])[0]
        question = store.question(goal['id'],task['id'],'Which child?')
        store.answer_question(family,goal['id'],question,'Amina')
        assert store.questions(goal['id'])[0]['state'] == 'answered'
        store.set_permission(family,'todoist','todoist.0',True)
        store.set_permission(family,'todoist','todoist.0',False)
        assert not store.permissions(family,'todoist')['todoist.0']
        ProviderEvents(store)
        assert store.get(family,goal['id'])['assignments'][0]['id'] == task['id']
    finally:
        store.delete(goal['id'])
        with store._connect() as db:
            db.execute('DELETE FROM plugin_permissions WHERE family_id=?',(family,))
