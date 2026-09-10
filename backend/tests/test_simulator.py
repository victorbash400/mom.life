import asyncio
from datetime import date
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.simulator import SimulatorService
from app.task_store import TaskStore
from plugins.runtime import PluginToolSession


class Families:
    def profile(self, family_id):
        return {"id": "adult", "name": "Sarah", "email": "sarah@example.com"}

    def list_children(self, family_id):
        return [{"id": "child", "name": "Noah"}, {"id": "sibling", "name": "Amina"}]

    def child(self, family_id, identity):
        return next((child for child in self.list_children(family_id) if child["id"] == identity), None)


def test_health_simulator_connects_seeds_and_loads_agent_tools(tmp_path):
    store = TaskStore(tmp_path / "simulator.db")
    service = SimulatorService(store, Families())

    state = service.connect("family", "apple-health")
    assert "apple-health" in store.installed_plugins("family")
    assert next(item for item in state["connections"] if item["id"] == "apple-health")["connected"] is True
    assert state["health"]["profiles"]["child"]["step_count"] > 0

    session = PluginToolSession(["apple-health"], store, "family")
    directory = asyncio.run(session.load("apple-health"))
    assert {tool["name"] for tool in directory} == {"read_daily_activity", "read_sleep", "read_heart_rate", "latest_sync"}
    result = asyncio.run(session.call("apple-health", "read_daily_activity", {"child_id": "child", "date": date.today().isoformat()}, "call"))
    assert {sample["sample_type"] for sample in result["data"]["samples"]} == {"step_count", "active_energy", "walking_running_distance"}


def test_simulated_whatsapp_reaches_the_real_intake_store(tmp_path, monkeypatch, auth_headers):
    from app import auth, main

    store = TaskStore(tmp_path / "simulator.db")
    families = Families()

    class Intake:
        async def receive(self, family_id, source, event_id, **content):
            return store.receive_incoming(family_id, source, event_id, **content)

    monkeypatch.setattr(main, "task_store", store)
    monkeypatch.setattr(main, "intake_agent", Intake())
    monkeypatch.setattr(main, "goal_tasks", SimpleNamespace(start=lambda *_: None))
    monkeypatch.setattr(auth, "families", families)
    SimulatorService(store, families).connect("family", "whatsapp")

    response = TestClient(main.app).post(
        "/api/simulator/whatsapp/messages",
        headers=auth_headers("family"),
        json={"profile_id": "child", "text": "My school trip form is due Friday."},
    )

    assert response.status_code == 201
    item = store.incoming_items("family")[0]
    assert item["source"] == "whatsapp"
    assert item["content"] == "My school trip form is due Friday."
    assert item["payload"]["simulated"] is True


def test_simulator_disconnect_does_not_remove_the_installed_plugin(tmp_path):
    store = TaskStore(tmp_path / "simulator.db")
    service = SimulatorService(store, Families())
    service.connect("family", "instacart")
    service.disconnect("family", "instacart")
    assert "instacart" in store.installed_plugins("family")
    assert "instacart" not in store.simulator_plugins("family")
