from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from app import main


client = TestClient(main.app)


@pytest.fixture(autouse=True)
def authenticated_client(auth_headers):
    client.headers.update(auth_headers('family-1'))
    yield
    client.headers.pop('Authorization', None)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_runtime_exposes_model_plan() -> None:
    response = client.get("/api/runtime")
    assert response.status_code == 200
    payload = response.json()
    assert payload["region"] == "us-east-1"
    assert payload["project_id"] == "proj_t6e6u24fw7kbzz5otsfo"
    assert payload["models"][0] == {
        "id": "moonshotai.kimi-k2.5",
        "purpose": "family agent",
        "enabled": True,
    }
    assert payload["models"][1]["enabled"] is False
    assert payload["models"][2]["enabled"] is False


def test_chat_stream_returns_sse(monkeypatch, tmp_path) -> None:
    async def fake_stream(**_: str) -> AsyncIterator[str]:
        yield 'data: {"type": "content", "content": "Ready"}\n\n'
        yield 'data: {"type": "done"}\n\n'

    from app import chat_routes
    from app.chat_sessions import ChatSessions
    monkeypatch.setattr(chat_routes, "chats", ChatSessions(tmp_path / "sessions"))
    chat = client.post("/api/chats").json()
    monkeypatch.setattr(main, "stream_agent_events", fake_stream)
    response = client.post(
        "/api/chat/stream",
        json={"chat_id": chat["id"], "message": "Hello"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"type": "content"' in response.text
    assert '"type": "done"' in response.text


def test_tasks_are_persisted_and_mutable(tmp_path, monkeypatch) -> None:
    from app.task_store import TaskStore

    from unittest.mock import AsyncMock
    monkeypatch.setattr(main, "task_store", TaskStore(tmp_path / "tasks.sqlite3"))
    monkeypatch.setattr(main, "goal_tasks", AsyncMock())
    from app.automation_manager import AutomationManager
    monkeypatch.setattr(main, "automations", AutomationManager(main.task_store,main.goal_tasks))
    created = client.post("/api/tasks", json={"child_id": "all", "text": "Book appointment"})
    assert created.status_code == 201
    task = created.json()
    assert task["status"] == "active"
    assert client.get("/api/tasks").json() == [task]
    paused = client.patch(f"/api/tasks/{task['id']}", json={"status": "paused"})
    assert paused.json()["status"] == "paused"
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 204
    assert client.get("/api/tasks").json() == []
