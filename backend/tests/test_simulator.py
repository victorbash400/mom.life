import asyncio
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.simulator import SimulatorService
from app.plugin_service import PluginService
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
    assert 8 <= state["health"]["profiles"]["child"]["sleep_analysis"] <= 9

    session = PluginToolSession(["apple-health"], store, "family")
    directory = asyncio.run(session.load("apple-health"))
    assert {tool["name"] for tool in directory} == {"read_daily_activity", "read_sleep", "read_heart_rate", "latest_sync"}
    result = asyncio.run(session.call("apple-health", "read_daily_activity", {"child_id": "child", "date": date.today().isoformat()}, "call"))
    assert {sample["sample_type"] for sample in result["data"]["samples"]} == {"step_count", "active_energy", "walking_running_distance"}


def test_simulated_whatsapp_reaches_the_real_intake_store(tmp_path, monkeypatch, auth_headers):
    from app import auth, main

    store = TaskStore(tmp_path / "simulator.db")
    families = Families()

    monkeypatch.setattr(main, "task_store", store)
    monkeypatch.setattr(main, "intake_agent", SimpleNamespace(start=AsyncMock()))
    monkeypatch.setattr(main, "security_agent", SimpleNamespace(receive=AsyncMock()))
    monkeypatch.setattr(main, "education_agent", SimpleNamespace(start=AsyncMock()))
    monkeypatch.setattr(main, "goal_tasks", SimpleNamespace(start=lambda *_: None))
    monkeypatch.setattr(auth, "families", families)
    SimulatorService(store, families).connect("family", "whatsapp")

    response = TestClient(main.app).post(
        "/api/simulator/whatsapp/messages",
        headers=auth_headers("family"),
        json={"profile_id": "child", "text": "My school trip form is due Friday."},
    )

    assert response.status_code == 201
    assert response.json()["message"]["body"] == "My school trip form is due Friday."
    item = store.incoming_items("family")[0]
    assert item["source"] == "whatsapp"
    assert item["content"] == "My school trip form is due Friday."
    assert item["payload"]["simulated"] is True
    assert item["payload"]["child_id"] == 'child'


def test_simulator_disconnect_does_not_remove_the_installed_plugin(tmp_path):
    store = TaskStore(tmp_path / "simulator.db")
    service = SimulatorService(store, Families())
    service.connect("family", "instacart")
    service.disconnect("family", "instacart")
    assert "instacart" in store.installed_plugins("family")
    assert "instacart" not in store.simulator_plugins("family")


def test_health_simulator_route_updates_a_child_sample(tmp_path, monkeypatch, auth_headers):
    from app import auth, main

    store = TaskStore(tmp_path / "simulator.db")
    families = Families()
    monkeypatch.setattr(main, "task_store", store)
    monkeypatch.setattr(auth, "families", families)
    SimulatorService(store, families).connect("family", "apple-health")

    response = TestClient(main.app).put(
        "/api/simulator/health",
        headers=auth_headers("family"),
        json={"child_id": "child", "date": date.today().isoformat(), "steps": 6500, "sleep_hours": 8.7, "heart_rate": 81, "active_energy": 249, "distance": 3599},
    )

    assert response.status_code == 200
    assert response.json()["profiles"]["child"]["step_count"] == 6500


def test_simulated_providers_are_connected_and_callable_by_assignments(tmp_path, monkeypatch):
    from app import auth

    store = TaskStore(tmp_path / "simulator.db")
    families = Families()
    monkeypatch.setattr(auth, "families", families)
    service = SimulatorService(store, families)
    for plugin_id in ("fitbit", "whatsapp", "instacart"):
        service.connect("family", plugin_id)

    states = {item["id"]: item for item in PluginService(store).list("family")}
    assert states["fitbit"]["connection_mode"] == "simulated"
    assert states["whatsapp"]["connected"] is True

    fitbit = PluginToolSession(["fitbit"], store, "family")
    asyncio.run(fitbit.load("fitbit"))
    activity = asyncio.run(fitbit.call("fitbit", "read_daily_activity", {"child_id": "child", "date": date.today().isoformat()}, "activity"))
    assert activity["data"]["samples"]

    whatsapp = PluginToolSession(["whatsapp"], store, "family")
    asyncio.run(whatsapp.load("whatsapp"))
    from app.event_stream import family_events
    updates = family_events.subscribe('family')
    asyncio.run(whatsapp.call("whatsapp", "send_text", {"to": "child", "text": "Your form is ready."}, "message"))
    assert updates.get_nowait()['type'] == 'simulator_changed'
    family_events.unsubscribe('family', updates)
    assert store.simulator_messages("family")[-1]["direction"] == "outgoing"

    instacart = PluginToolSession(["instacart"], store, "family")
    asyncio.run(instacart.load("instacart"))
    result = asyncio.run(instacart.call("instacart", "prepare_shopping_list", {"items": "milk, apples"}, "shopping"))
    assert result["data"]["action"] == "prepare_shopping_list"
