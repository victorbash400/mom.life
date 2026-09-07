import asyncio
import json
import pytest
from fastapi.testclient import TestClient
from app import main, chat_routes, chat_stream
from app.chat_store import ChatStore


@pytest.fixture
def store(tmp_path, monkeypatch):
    store = ChatStore(tmp_path / 'chats.sqlite3')
    monkeypatch.setattr(chat_routes, 'chats', store)
    return store


def test_history_persists_and_is_family_scoped(store, auth_headers):
    client = TestClient(main.app)
    client.headers.update(auth_headers('one'))
    chat = client.post('/api/chats').json()
    store.append('one', chat['id'], 'user', 'Plan the school week')
    store.append('one', chat['id'], 'assistant', 'What time does school start?')
    reopened = ChatStore(store.target).get('one', chat['id'])
    assert reopened['title'] == 'Plan the school week'
    assert len(reopened['messages']) == 2
    assert client.get('/api/chats').json()[0]['id'] == chat['id']
    client.headers.update(auth_headers('two'))
    assert client.get('/api/chats').json() == []
    assert client.get(f"/api/chats/{chat['id']}").status_code == 404
    assert client.delete(f"/api/chats/{chat['id']}").status_code == 404
    assert client.post('/api/chat/stream', json={'family_id': 'two', 'chat_id': chat['id'], 'message': 'hello'}).status_code == 404
    client.headers.update(auth_headers('one'))
    assert client.delete(f"/api/chats/{chat['id']}").status_code == 204
    assert client.get('/api/chats').json() == []


def test_stream_saves_reply_and_surfaces_errors(store, monkeypatch):
    asyncio.run(check_stream(store, monkeypatch))


async def check_stream(store, monkeypatch):
    class Agent:
        async def stream_async(self, message):
            yield {'data': 'Hello '}
            yield {'data': 'there'}
    monkeypatch.setattr(chat_stream, 'create_mom_life_agent', lambda *args, **kwargs: Agent())
    chat = store.create('one')
    events = [json.loads(event[6:]) async for event in chat_stream.stream_agent_events(family_id='one', chat_id=chat['id'], message='Hi')]
    assert events[-1]['type'] == 'done'
    assert [message['content'] for message in store.get('one', chat['id'])['messages']] == ['Hi', 'Hello there']
    def fail(*args, **kwargs):
        raise RuntimeError('Provider unavailable')
    monkeypatch.setattr(chat_stream, 'create_mom_life_agent', fail)
    events = [event async for event in chat_stream.stream_agent_events(family_id='one', chat_id=chat['id'], message='Again')]
    assert 'Provider unavailable' in events[-1]
    assert store.get('one', chat['id'])['messages'][-1]['content'] == 'Again'
