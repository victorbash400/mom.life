import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from agents import intake_agent as intake_runtime
from app.intake_agent import IntakeAgentManager
from app.task_store import TaskStore


class Families:
    @staticmethod
    def list_children(family_id):
        return [{"id": "child", "family_id": family_id, "name": "Noah"}]

    @staticmethod
    def profile(family_id):
        return {"id": "parent", "family_id": family_id, "name": "Sarah"}

    @staticmethod
    def child(family_id, child_id):
        return {"id": child_id, "family_id": family_id} if child_id == "child" else None


def test_incoming_items_accept_any_source_and_deduplicate(tmp_path):
    store = TaskStore(tmp_path / "intake.db")
    first, created = store.receive_incoming(
        "family",
        "school-portal",
        "notice-1",
        sender="School",
        subject="Trip",
        content="Permission is due Friday.",
        payload={"anything": ["the", "source", "provides"]},
    )
    repeated, repeated_created = store.receive_incoming("family", "school-portal", "notice-1")
    assert created is True
    assert repeated_created is False
    assert repeated["id"] == first["id"]
    assert first["payload"]["anything"][2] == "provides"


def test_intake_agent_records_one_flexible_decision(tmp_path, monkeypatch):
    from app import auth

    store = TaskStore(tmp_path / "decision.db")
    item, _ = store.receive_incoming("family", "email", "message-1", sender="teacher@example.com", content="Newsletter only")
    store.set_incoming(item["id"], status="processing")
    monkeypatch.setattr(auth, "families", Families())

    class Agent:
        def __init__(self, **kwargs):
            self.tools = {item.tool_name: item for item in kwargs["tools"]}

        async def stream_async(self, prompt):
            context = self.tools["read_intake_context"]()
            assert context["incoming"]["source"] == "email"
            assert context["family"]["children"][0]["name"] == "Noah"
            skill = self.tools["read_intake_routing_skill"]()
            assert skill["name"] == "Incoming Information Routing"
            self.tools["update_intake_memory"]("all", "The school newsletter is the latest family information received.")
            self.tools["decide_intake_action"]("record_only", "This newsletter requests no family action.", note="Retained with its source.")
            yield {}

    monkeypatch.setattr(intake_runtime, "Agent", Agent)
    monkeypatch.setattr(intake_runtime, "BedrockModel", lambda **kwargs: None)
    result = asyncio.run(intake_runtime.run_intake_agent(store, "family", str(item["id"])))
    saved = store.incoming(str(item["id"]), "family")
    assert result["action"] == "record_only"
    assert saved["status"] == "completed"
    assert saved["action"] == "record_only"
    assert saved["activities"][-1]["detail"]["note"] == "Retained with its source."
    assert store.intake_memory("family")["all"].startswith("The school newsletter")


def test_manager_dispatches_created_goal_to_existing_goal_system(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / "dispatch.db")
    item, _ = store.receive_incoming("family", "whatsapp", "message-2", content="Please arrange pickup.")
    goals = AsyncMock()

    async def decide(_store, family_id, incoming_id):
        goal = store.create(family_id, "child", "Arrange pickup")
        store.set_incoming(incoming_id, status="completed", action="create_goal", goal_id=goal["id"], child_id="child")
        return {"action": "create_goal", "goal_id": goal["id"], "child_id": "child"}

    from app import intake_agent as manager_module
    monkeypatch.setattr(manager_module, "run_intake_agent", decide)
    manager = IntakeAgentManager(store, goals)
    asyncio.run(manager._run("family", str(item["id"])))
    goals.start.assert_awaited_once()
    assert store.incoming(str(item["id"]), "family")["status"] == "completed"


def test_retry_preserves_prior_goal_link_for_duplicate_avoidance(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / "retry.db")
    item, _ = store.receive_incoming("family", "email", "message-3", content="Updated information")
    goal = store.create("family", "child", "Existing outcome")
    store.set_incoming(item["id"], status="failed", action="create_goal", goal_id=goal["id"], child_id="child", failure="Dispatch failed")
    manager = IntakeAgentManager(store, AsyncMock())
    monkeypatch.setattr(manager, "start", AsyncMock(return_value=True))
    retried = asyncio.run(manager.retry("family", str(item["id"])))
    assert retried["goal_id"] == goal["id"]
    assert retried["child_id"] == "child"
    assert retried["status"] == "queued"
