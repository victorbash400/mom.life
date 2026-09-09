import asyncio
from unittest.mock import AsyncMock

from agents import education_agent as education_runtime
from app.education_agent import EducationAgentManager
from app.intake_agent import IntakeAgentManager
from app.task_store import TaskStore


class Families:
    @staticmethod
    def list_children(family_id):
        return [{"id": "child", "family_id": family_id, "name": "Amina"}]

    @staticmethod
    def child(family_id, child_id):
        return {"id": child_id, "family_id": family_id, "name": "Amina"} if child_id == "child" else None


def test_education_snapshot_keeps_source_evidence(tmp_path):
    store = TaskStore(tmp_path / "education.db")
    store.update_education_snapshot("family", "child", "Amina is reading longer stories.", "message-1")
    saved = store.update_education_snapshot("family", "child", "Amina is reading longer stories and discussing them confidently.", "message-2")
    assert saved["summary"].endswith("confidently.")
    assert saved["source_ids"] == ["message-1", "message-2"]
    assert store.education_snapshots("other") == []
    store.delete_education_snapshot("family", "child")
    assert store.education_snapshot("family", "child") is None


def test_education_agent_updates_natural_language_snapshot(tmp_path, monkeypatch):
    from app import auth

    store = TaskStore(tmp_path / "agent.db")
    incoming, _ = store.receive_incoming("family", "email", "message-1", content="Amina is now reading chapter books independently.")
    review, _ = store.receive_education_review("family", str(incoming["id"]))
    store.set_education_review(str(review["id"]), status="processing")
    monkeypatch.setattr(auth, "families", Families())

    class Agent:
        def __init__(self, **kwargs):
            self.tools = {item.tool_name: item for item in kwargs["tools"]}

        async def stream_async(self, prompt):
            context = self.tools["read_education_context"]()
            assert context["incoming"]["source"] == "email"
            assert context["snapshots"] == []
            skill = self.tools["read_education_snapshot_skill"]()
            assert skill["name"] == "Education Snapshot Maintenance"
            self.tools["update_education_snapshot"]("child", "Amina is reading chapter books independently.")
            self.tools["complete_education_review"]("The source confirms a meaningful change in Amina's reading.")
            yield {}

    monkeypatch.setattr(education_runtime, "Agent", Agent)
    monkeypatch.setattr(education_runtime, "BedrockModel", lambda **kwargs: None)
    result = asyncio.run(education_runtime.run_education_agent(store, "family", str(review["id"])))
    assert result == {"action": "update", "child_ids": ["child"]}
    assert store.education_snapshot("family", "child")["summary"].startswith("Amina is reading")


def test_education_agent_exposes_connected_provider_read_tools(tmp_path, monkeypatch):
    from app import auth

    store = TaskStore(tmp_path / "provider.db")
    store.install_plugin("family", "google-classroom")
    with store._connect() as connection:
        connection.execute("INSERT INTO plugin_connections VALUES (?,?,?)", ("family", "google-classroom", "now"))
    incoming, _ = store.receive_incoming("family", "email", "message-provider", content="Classroom update")
    review, _ = store.receive_education_review("family", str(incoming["id"]))
    store.set_education_review(str(review["id"]), status="processing")
    monkeypatch.setattr(auth, "families", Families())

    class ProviderSession:
        def __init__(self, plugin_ids, store, family_id):
            assert plugin_ids == ["google-classroom"]

        async def load(self, plugin_id):
            return [{"name": "list_courses", "requires_approval": False}, {"name": "write_course", "requires_approval": True}]

        async def call(self, plugin_id, name, arguments, call_id):
            assert (plugin_id, name, arguments) == ("google-classroom", "list_courses", {})
            return {"courses": [{"name": "Reading"}]}

        async def close(self):
            return None

    class Agent:
        def __init__(self, **kwargs):
            self.tools = {item.tool_name: item for item in kwargs["tools"]}

        async def stream_async(self, prompt):
            context = self.tools["read_education_context"]()
            assert context["connected_sources"] == ["google-classroom"]
            directory = await self.tools["list_education_source_tools"]("google-classroom")
            assert [item["name"] for item in directory] == ["list_courses"]
            result = await self.tools["read_education_source"]("google-classroom", "list_courses", {})
            assert result["courses"][0]["name"] == "Reading"
            self.tools["complete_education_review"]("The source did not identify a known child.")
            yield {}

    monkeypatch.setattr(education_runtime, "PluginToolSession", ProviderSession)
    monkeypatch.setattr(education_runtime, "Agent", Agent)
    monkeypatch.setattr(education_runtime, "BedrockModel", lambda **kwargs: None)
    result = asyncio.run(education_runtime.run_education_agent(store, "family", str(review["id"])))
    assert result["action"] == "ignore"


def test_intake_dispatches_created_item_to_education_agent(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / "dispatch.db")
    security = AsyncMock()
    education = AsyncMock()
    manager = IntakeAgentManager(store, AsyncMock(), security, education)
    monkeypatch.setattr(manager, "start", AsyncMock(return_value=True))
    item, created = asyncio.run(manager.receive("family", "upload", "file-1", content="School report"))
    assert created is True
    education.receive.assert_awaited_once_with("family", item["id"])


def test_education_manager_records_irrelevant_items_without_snapshot(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / "manager.db")
    incoming, _ = store.receive_incoming("family", "email", "message-2", content="A grocery receipt")
    review, _ = store.receive_education_review("family", str(incoming["id"]))

    async def ignore(store, family_id, review_id):
        store.set_education_review(review_id, status="completed", action="ignore", reason="This is not education information.")
        return {"action": "ignore", "child_ids": []}

    monkeypatch.setattr("app.education_agent.run_education_agent", ignore)
    manager = EducationAgentManager(store)
    asyncio.run(manager._run("family", str(review["id"])))
    assert store.education_review(str(review["id"]), "family")["action"] == "ignore"
    assert store.education_snapshots("family") == []


def test_education_manager_recovers_unreviewed_evidence(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / "recovery.db")
    incoming, _ = store.receive_incoming("family", "upload", "file-2", content="School report")
    manager = EducationAgentManager(store)
    monkeypatch.setattr(manager, "start", AsyncMock(return_value=True))
    asyncio.run(manager.recover())
    with store._connect() as connection:
        review = connection.execute("SELECT * FROM education_reviews WHERE incoming_id=?", (incoming["id"],)).fetchone()
    assert review is not None
    manager.start.assert_awaited_once_with("family", review["id"])
