import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from agents import intake_agent as intake_runtime
from app.intake_agent import IntakeAgentManager
from app.task_store import TaskStore


class Families:
    @classmethod
    def snapshot(cls, family_id):
        return cls.profile(family_id), cls.list_children(family_id)

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


def test_incoming_replay_window_deduplicates_distinct_provider_ids(tmp_path):
    store = TaskStore(tmp_path / "replay.db")
    details = {"correlation": "thread-1", "sender": "School", "subject": "Trip", "content": "Permission is due Friday."}
    first, created = store.receive_incoming("family", "email", "message-1", **details)
    replay, replay_created = store.receive_incoming("family", "email", "message-2", **details)
    follow_up, follow_up_created = store.receive_incoming(
        "family", "email", "message-3", **{**details, "content": "The deadline moved to Monday."},
    )
    assert created is True
    assert replay_created is False
    assert replay["id"] == first["id"]
    assert follow_up_created is True
    assert follow_up["id"] != first["id"]


def test_simulator_ingest_persists_one_review_bundle_for_replay(tmp_path):
    store = TaskStore(tmp_path / "simulator-bundle.db")
    store.set_simulator_plugin("family", "whatsapp", True)
    payload = {"simulated": True}
    first = store.receive_simulator_incoming("family", "parent", "Sarah (Simulator)", "Same update", "event-1", payload)
    replay = store.receive_simulator_incoming("family", "parent", "Sarah (Simulator)", "Same update", "event-2", payload)
    assert first["created"] is True
    assert {key: replay[key] for key in ("created", "duplicate", "matched", "goal_ids", "incoming_id")} == {
        "created": False, "duplicate": False, "matched": False, "goal_ids": [], "incoming_id": first["incoming_id"],
    }
    assert replay["message"]["body"] == "Same update"
    assert len(store.incoming_items("family")) == 1
    assert len(store.security_reviews("family")) == 1
    with store._connect() as connection:
        assert connection.execute("SELECT COUNT(*) AS count FROM education_reviews").fetchone()["count"] == 1
        assert connection.execute("SELECT COUNT(*) AS count FROM simulator_messages").fetchone()["count"] == 2


def test_deleting_incoming_removes_its_reviews(tmp_path):
    store = TaskStore(tmp_path / "delete-incoming.db")
    item, _ = store.receive_incoming("family", "email", "message", content="School update")
    store.receive_security_review("family", item["id"])
    store.receive_education_review("family", item["id"])
    assert store.delete_incoming("family", item["id"])
    assert store.incoming(item["id"], "family") is None
    assert store.security_reviews("family") == []
    with store._connect() as connection:
        assert connection.execute("SELECT id FROM education_reviews WHERE incoming_id=?", (item["id"],)).fetchone() is None


def test_recovery_bounds_live_runtime_leases(tmp_path, monkeypatch):
    from app import intake_agent as manager_module
    store = TaskStore(tmp_path / "recovery-capacity.db")
    for index in range(12):
        store.receive_incoming(f"family-{index}", "email", f"message-{index}", content="Queued item")
    active = 0
    peak = 0
    gate = asyncio.Event()

    def acquire(*args):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        return object()

    def release(lease):
        nonlocal active
        active -= 1

    async def run():
        manager = IntakeAgentManager(store, AsyncMock())
        monkeypatch.setattr(manager_module, "acquire_wait", acquire)
        monkeypatch.setattr(manager_module, "release", release)
        async def blocked(*args):
            await gate.wait()
        monkeypatch.setattr(manager, "_run", blocked)
        await manager.recover()
        await asyncio.sleep(0)
        assert peak == 4
        gate.set()
        await asyncio.gather(*list(manager._tasks.values()))

    asyncio.run(run())
    assert active == 0


def test_same_family_intake_is_serial(tmp_path, monkeypatch):
    from app import intake_agent as manager_module
    store = TaskStore(tmp_path / "family-order.db")
    items = [store.receive_incoming("family", "email", f"message-{index}", content="Update")[0] for index in range(2)]
    active = 0
    peak = 0

    async def run():
        manager = IntakeAgentManager(store, AsyncMock())
        monkeypatch.setattr(manager_module, "acquire_wait", lambda *args: object())
        monkeypatch.setattr(manager_module, "release", lambda lease: None)
        async def work(*args):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0)
            active -= 1
        monkeypatch.setattr(manager, "_run", work)
        for item in items:
            await manager.start("family", item["id"], known_runnable=True)
        await asyncio.gather(*list(manager._tasks.values()))

    asyncio.run(run())
    assert peak == 1


def test_intake_agent_records_one_flexible_decision(tmp_path, monkeypatch):
    from app import auth

    store = TaskStore(tmp_path / "decision.db")
    item, _ = store.receive_incoming("family", "email", "message-1", sender="teacher@example.com", content="Newsletter only")
    store.set_incoming(item["id"], status="processing")
    monkeypatch.setattr(auth, "families", Families())

    class Agent:
        def __init__(self, **kwargs):
            self.tools = {item.tool_name: item for item in kwargs["tools"]}

        def cancel(self):
            pass

        async def invoke_async(self, prompt):
            context = await self.tools["read_intake_context"]()
            assert context["incoming"]["source"] == "email"
            assert context["family"]["children"][0]["name"] == "Noah"
            skill = await self.tools["read_intake_routing_skill"]()
            assert skill["name"] == "Incoming Information Routing"
            await self.tools["update_intake_memory"]("all", "The school newsletter is the latest family information received.")
            await self.tools["decide_intake_action"]("record_only", "This newsletter requests no family action.", note="Retained with its source.")

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
