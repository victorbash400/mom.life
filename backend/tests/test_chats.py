import asyncio
import json
import sqlite3
from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from strands.types.session import SessionAgent, SessionMessage

from app import chat_routes, chat_stream, main
from app.chat_sessions import AGENT_ID, ChatSessions


def test_cloud_first_send_registers_chat_without_changing_ownership(tmp_path, monkeypatch):
    database = tmp_path / "chats.db"
    @contextmanager
    def connect(_):
        with sqlite3.connect(database) as db:
            db.row_factory = sqlite3.Row
            yield db
    monkeypatch.setattr("app.chat_sessions.connect", connect)
    with connect("") as db:
        db.execute("CREATE TABLE chats(id TEXT PRIMARY KEY,family_id TEXT,title TEXT,created_at TEXT,updated_at TEXT)")
    sessions = ChatSessions(database=str(database))
    identity = str(uuid4())
    assert sessions.ensure("one", identity) == identity
    assert sessions.ensure("one", identity) == identity
    with pytest.raises(ValueError, match="Chat not found"):
        sessions.ensure("two", identity)
    assert len(sessions.list("one")) == 1
    assert sessions.list("two") == []


@pytest.fixture
def store(tmp_path, monkeypatch):
    sessions = ChatSessions(tmp_path / "sessions")
    monkeypatch.setattr(chat_routes, "chats", sessions)
    return sessions


def add_messages(store, family_id, chat_id, *messages):
    manager = store.ensure(family_id, chat_id)
    manager.create_agent(chat_id, SessionAgent(agent_id=AGENT_ID, state={}, conversation_manager_state={}))
    for index, (role, content) in enumerate(messages):
        manager.create_message(chat_id, AGENT_ID, SessionMessage.from_message({"role": role, "content": [{"text": content}]}, index))


def test_history_is_owned_by_strands_and_family_scoped(store, auth_headers):
    client = TestClient(main.app)
    client.headers.update(auth_headers("one"))
    chat = client.post("/api/chats").json()
    add_messages(store, "one", chat["id"], ("user", "Plan the school week"), ("assistant", "What time does school start?"))
    reopened = ChatSessions(store.root).get("one", chat["id"])
    assert reopened["title"] == "Plan the school week"
    assert [message["content"] for message in reopened["messages"]] == ["Plan the school week", "What time does school start?"]
    assert client.get("/api/chats").json()[0]["id"] == chat["id"]
    client.headers.update(auth_headers("two"))
    assert client.get("/api/chats").json() == []
    assert client.get(f"/api/chats/{chat['id']}").status_code == 404
    assert client.delete(f"/api/chats/{chat['id']}").status_code == 404
    client.headers.update(auth_headers("one"))
    assert client.delete(f"/api/chats/{chat['id']}").status_code == 204
    assert client.get("/api/chats").json() == []


def test_stream_uses_the_strands_session_without_copying_messages(store, monkeypatch):
    asyncio.run(check_stream(store, monkeypatch))


async def check_stream(store, monkeypatch):
    chat = store.create("one")

    class Agent:
        def __init__(self, manager):
            self.manager = manager

        async def stream_async(self, message):
            self.manager.create_agent(chat["id"], SessionAgent(agent_id=AGENT_ID, state={}, conversation_manager_state={}))
            self.manager.create_message(chat["id"], AGENT_ID, SessionMessage.from_message({"role": "user", "content": [{"text": message}]}, 0))
            yield {"data": "Hello "}
            yield {"data": "there"}
            self.manager.create_message(chat["id"], AGENT_ID, SessionMessage.from_message({"role": "assistant", "content": [{"text": "Hello there"}]}, 1))

    monkeypatch.setattr(chat_stream, "create_mom_life_agent", lambda *args, session_manager, **kwargs: Agent(session_manager))
    events = [json.loads(event[6:]) async for event in chat_stream.stream_agent_events(family_id="one", chat_id=chat["id"], message="Hi")]
    assert events[-1]["type"] == "done"
    assert [message["content"] for message in store.get("one", chat["id"])["messages"]] == ["Hi", "Hello there"]

    def fail(*args, **kwargs):
        raise RuntimeError("Provider unavailable")

    monkeypatch.setattr(chat_stream, "create_mom_life_agent", fail)
    events = [event async for event in chat_stream.stream_agent_events(family_id="one", chat_id=chat["id"], message="Again")]
    assert "Provider unavailable" in events[-1]


def test_tool_history_preserves_order_and_result_status(store):
    chat = store.create("one")
    manager = store.ensure("one", chat["id"])
    manager.create_agent(chat["id"], SessionAgent(agent_id=AGENT_ID, state={}, conversation_manager_state={}))
    blocks = [
        {"role": "assistant", "content": [{"text": "Checking."}, {"toolUse": {"toolUseId": "call-1", "name": "get_family_context", "input": {}}}]},
        {"role": "user", "content": [{"toolResult": {"toolUseId": "call-1", "status": "success", "content": [{"text": "Private result"}]}}]},
        {"role": "assistant", "content": [{"text": "Done."}]},
    ]
    for index, message in enumerate(blocks):
        manager.create_message(chat["id"], AGENT_ID, SessionMessage.from_message(message, index))
    messages = store.get("one", chat["id"])["messages"]
    assert len(messages) == 3
    assert messages[0]["content"] == "Checking."
    assert messages[1] == {"id": "call-1", "kind": "tool", "name": "get_family_context", "status": "done"}
    assert messages[2]["content"] == "Done."


def test_stream_deduplicates_strands_tool_deltas(store, monkeypatch):
    chat = store.create("one")

    class Agent:
        async def stream_async(self, message):
            yield {"current_tool_use": {"toolUseId": "call-1", "name": "get_current_datetime", "input": ""}}
            yield {"current_tool_use": {"toolUseId": "call-1", "name": "get_current_datetime", "input": "{}"}}
            recorder._completed.append({"id": "call-1", "name": "get_current_datetime", "status": "done"})
            yield {"data": "Today"}

    def create(session_id, tool_events, **kwargs):
        nonlocal recorder
        recorder = tool_events
        return Agent()

    recorder = None
    monkeypatch.setattr(chat_stream, "create_mom_life_agent", create)

    async def collect():
        return [json.loads(event[6:]) async for event in chat_stream.stream_agent_events(family_id="one", chat_id=chat["id"], message="Date?")]

    events = asyncio.run(collect())
    assert [event["type"] for event in events] == ["tool_call", "tool_response", "content", "done"]
