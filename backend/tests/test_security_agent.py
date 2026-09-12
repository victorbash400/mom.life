import asyncio
from unittest.mock import AsyncMock

from agents import security_agent as security_runtime
from app.intake_agent import IntakeAgentManager
from app.security_agent import SecurityAgentManager
from app.task_store import TaskStore


class Families:
    @classmethod
    def snapshot(cls, family_id):
        return cls.profile(family_id), cls.list_children(family_id)

    @staticmethod
    def list_children(family_id):
        return [{"id": "child", "family_id": family_id, "name": "Noah", "notifications": True}]

    @staticmethod
    def profile(family_id):
        return {"id": "parent", "family_id": family_id, "name": "Sarah"}

    @staticmethod
    def child(family_id, child_id):
        return {"id": child_id, "family_id": family_id} if child_id == "child" else None


def test_policy_scope_depth_and_manual_checks(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / 'policy.db')
    saved = store.update_security_settings('family',True,'important','Review account access',
        sources=['email'],child_ids=['child'],depth='recent',review_mode='manual',channel='in_app')
    assert saved['sources'] == ['email'] and saved['review_mode'] == 'manual'
    item, _ = store.receive_incoming('family','email','scoped',content='New account access',payload={'child_id':'child'})
    store.receive_incoming('family','upload','excluded',content='Private excluded file',payload={'child_id':'child'})
    store.receive_incoming('other','email','other-family',content='Other family',payload={'child_id':'child'})
    assert [entry['id'] for entry in store.security_context_slice('family',saved)] == [item['id']]
    manager = SecurityAgentManager(store)
    start = AsyncMock(return_value=True)
    monkeypatch.setattr(manager,'start',start)
    review, _ = asyncio.run(manager.receive('family',item['id']))
    start.assert_not_awaited()
    assert store.security_review(review['id'],'family')['action'] == 'ignore'
    _, queued = asyncio.run(manager.receive('family',item['id'],manual=True))
    assert queued
    start.assert_awaited_once()
    assert store.security_review(review['id'],'family')['status'] == 'queued'


def test_security_settings_and_alert_lifecycle(tmp_path):
    store = TaskStore(tmp_path / "security.db")
    assert store.security_settings("family")["alert_level"] == "important"
    saved = store.update_security_settings("family", True, "urgent", "Alert me about unknown account access.")
    assert saved["enabled"] is True
    assert saved["instructions"].startswith("Alert me")
    incoming, _ = store.receive_incoming("family", "email", "message-1", content="A new device signed in.")
    review, created = store.receive_security_review("family", str(incoming["id"]))
    assert created is True
    store.set_security_review(review["id"], status="completed", action="alert", severity="high", summary="Unknown sign-in", reason="A new device accessed the account.")
    assert store.security_reviews("family")[0]["incoming"]["source"] == "email"
    assert store.dismiss_security_alert("family", str(review["id"])) is True
    assert store.security_review(str(review["id"]), "family")["dismissed"] is True


def test_security_agent_uses_settings_and_records_one_decision(tmp_path, monkeypatch):
    from app import auth

    store = TaskStore(tmp_path / "decision.db")
    store.update_security_settings("family", True, "all", "Show credible account access concerns.")
    incoming, _ = store.receive_incoming("family", "email", "message-2", content="A new device signed in to the school account.")
    review, _ = store.receive_security_review("family", str(incoming["id"]))
    store.set_security_review(review["id"], status="processing")
    monkeypatch.setattr(auth, "families", Families())

    class Agent:
        def __init__(self, **kwargs):
            self.tools = {item.tool_name: item for item in kwargs["tools"]}

        def cancel(self):
            pass

        async def invoke_async(self, prompt):
            context = await self.tools["read_security_context"]()
            assert context["settings"]["alert_level"] == "all"
            assert context["incoming"]["source"] == "email"
            skill = await self.tools["read_security_monitoring_skill"]()
            assert skill["name"] == "Family Safety Monitoring"
            await self.tools["decide_security_action"](
                "alert",
                "The message reports account access from a new device.",
                severity="high",
                category="Account access",
                summary="New device accessed the school account",
                child_id="child",
            )

    monkeypatch.setattr(security_runtime, "Agent", Agent)
    monkeypatch.setattr(security_runtime, "BedrockModel", lambda **kwargs: None)
    result = asyncio.run(security_runtime.run_security_agent(store, "family", str(review["id"])))
    saved = store.security_review(str(review["id"]), "family")
    assert result["action"] == "alert"
    assert saved["severity"] == "high"
    assert saved["summary"].startswith("New device")


def test_intake_dispatches_created_item_to_security_agent(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / "dispatch.db")
    security = AsyncMock()
    manager = IntakeAgentManager(store, AsyncMock(), security)
    monkeypatch.setattr(manager, "start", AsyncMock(return_value=True))
    item, created = asyncio.run(manager.receive("family", "upload", "file-1", content="Evidence"))
    assert created is True
    security.receive.assert_awaited_once_with("family", item["id"])


def test_disabled_security_monitoring_stays_quiet(tmp_path):
    store = TaskStore(tmp_path / "disabled.db")
    store.update_security_settings("family", False, "important", "")
    incoming, _ = store.receive_incoming("family", "upload", "file-2", content="Routine document")
    review, _ = store.receive_security_review("family", str(incoming["id"]))
    manager = SecurityAgentManager(store)
    asyncio.run(manager._run("family", str(review["id"])))
    saved = store.security_review(str(review["id"]), "family")
    assert saved["action"] == "ignore"
    assert saved["reason"] == "Safety monitoring is turned off."


def test_prequeued_simulator_review_respects_manual_mode(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / 'manual-simulator.db')
    store.set_simulator_plugin('family', 'whatsapp', True)
    store.update_security_settings('family', True, 'important', '', review_mode='manual', child_ids=['child'])
    routed = store.receive_simulator_incoming('family', 'child', 'Noah', 'Please review this message', 'sim-manual', {'child_id':'child'})
    manager = SecurityAgentManager(store)
    start = AsyncMock()
    monkeypatch.setattr(manager, 'start', start)
    asyncio.run(manager.receive('family', routed['incoming_id']))
    start.assert_not_called()
    assert store.security_review(routed['security_id'], 'family')['action'] == 'ignore'
    asyncio.run(manager.receive('family', routed['incoming_id'], manual=True))
    start.assert_called_once_with('family', routed['security_id'], known_runnable=True)
