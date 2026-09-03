from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from app import main


client = TestClient(main.app)


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


def test_chat_stream_returns_sse(monkeypatch) -> None:
    async def fake_stream(**_: str) -> AsyncIterator[str]:
        yield 'data: {"type": "content", "content": "Ready"}\n\n'
        yield 'data: {"type": "done"}\n\n'

    monkeypatch.setattr(main, "stream_agent_events", fake_stream)
    response = client.post(
        "/api/chat/stream",
        json={"family_id": "family-1", "chat_id": "chat-1", "message": "Hello"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"type": "content"' in response.text
    assert '"type": "done"' in response.text


def test_tasks_are_persisted_and_mutable(tmp_path, monkeypatch) -> None:
    from app.task_store import TaskStore

    monkeypatch.setattr(main, "task_store", TaskStore(tmp_path / "tasks.sqlite3"))
    created = client.post("/api/tasks", json={"family_id": "family-1", "child_id": "child-1", "text": "Book appointment"})
    assert created.status_code == 201
    task = created.json()
    assert task["status"] == "active"
    assert client.get("/api/tasks?family_id=family-1").json() == [task]
    paused = client.patch(f"/api/tasks/{task['id']}", json={"status": "paused"})
    assert paused.json()["status"] == "paused"
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 204
    assert client.get("/api/tasks?family_id=family-1").json() == []
