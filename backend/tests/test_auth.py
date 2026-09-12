import sqlite3
import time
from fastapi.testclient import TestClient
from app import auth, main


def test_demo_login_revocation_and_expiry(auth_headers):
    client = TestClient(main.app)
    assert client.get('/api/tasks?family_id=sarah-family').status_code == 401
    assert client.post('/api/auth/login', json={'email': auth.DEMO_EMAIL, 'password': 'wrong'}).status_code == 401
    response = client.post('/api/auth/login', json={'email': auth.DEMO_EMAIL, 'password': auth.DEMO_PASSWORD})
    family_id = response.json()['family_id']
    assert family_id == 'sarah-family'
    assert response.json()['expires_in'] == 60 * 60 * 24 * 30
    token = response.json()['token']
    client.headers['Authorization'] = f'Bearer {token}'
    session = client.get('/api/auth/session').json()
    assert session['family_id'] == family_id
    assert session['name'] == 'Sarah'
    assert session['demo'] is True
    assert client.get('/api/tasks?family_id=other').status_code == 403
    assert client.post('/api/tasks', json={'family_id': 'other', 'child_id': 'child', 'text': 'No access'}).status_code == 403
    with sqlite3.connect(auth.sessions.path) as db:
        assert token not in str(db.execute('SELECT * FROM auth_sessions').fetchall())
    assert client.post('/api/auth/logout').status_code == 204
    assert client.get('/api/auth/session').status_code == 401
    client.headers.update(auth_headers('sarah-family'))
    with sqlite3.connect(auth.sessions.path) as db:
        db.execute('UPDATE auth_sessions SET expires_at=?', (time.time() - 1,))
    assert client.get('/api/auth/session').status_code == 401


def test_all_family_surfaces_require_login(auth_headers):
    client = TestClient(main.app)
    for path in ['tasks', 'plugins', 'skills', 'runtime', 'tasks/events', 'security']:
        assert client.get(f'/api/{path}?family_id=sarah-family').status_code == 401
    assert client.post('/api/chat/stream', json={'family_id':'sarah-family','message':'Hi','chat_id':'test'}).status_code == 401
    assert client.get('/health').status_code == 200

    client.headers.update(auth_headers('missing-family'))
    assert client.get('/api/auth/session').status_code == 401
    assert client.get('/api/family').status_code == 401
