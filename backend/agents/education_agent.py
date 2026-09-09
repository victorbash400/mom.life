import json

import boto3
from strands import Agent, tool
from strands.hooks import BeforeToolCallEvent, HookRegistry
from strands.models import BedrockModel
from strands.tools.executors import SequentialToolExecutor

from app.config import Settings, get_settings
from app.task_store import TaskStore, now
from plugins.catalog import PLUGINS
from plugins.runtime import PluginToolSession


EDUCATION_PROMPT = """You are mom.life's Education Agent. Review exactly one incoming family item and keep each known child's education snapshot useful for Mom.

Use tools for every read and write. Read the original evidence, known children, existing snapshots, and the family's Education Snapshot Maintenance skill. Do not use keyword rules and do not invent a child, curriculum, subject, grade, ability, attendance figure, deadline, or result.

When confirmed information materially improves a known child's education picture, call update_education_snapshot with a complete natural-language snapshot that preserves still-relevant prior context. The snapshot should explain what the child is learning, how things appear to be going, meaningful changes, and anything important for Mom to know. It may be as short or detailed as the evidence warrants. Update every affected known child, and never force unrelated information into a snapshot.

Call complete_education_review exactly once after any updates, or immediately when the item adds nothing useful. Do not create tasks, contact anyone, or make education decisions. End after completion is confirmed."""


class _StopAfterCompletion:
    def __init__(self, result: dict[str, object]) -> None:
        self.result = result

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before)

    def before(self, event: BeforeToolCallEvent) -> None:
        if self.result:
            event.cancel_tool = "This education review is already complete."


async def run_education_agent(store: TaskStore, family_id: str, review_id: str, settings: Settings | None = None) -> dict[str, object]:
    result: dict[str, object] = {}
    updated_children: list[str] = []
    with store._connect() as connection:
        connected = {
            row["plugin_id"]
            for row in connection.execute("SELECT plugin_id FROM plugin_connections WHERE family_id=?", (family_id,)).fetchall()
        }
    education_plugins = [plugin.id for plugin in PLUGINS if plugin.group == "Education" and plugin.id in connected]
    providers = PluginToolSession(education_plugins, store, family_id)

    async def load_read_tools(plugin_id: str) -> list[dict[str, object]]:
        if plugin_id not in education_plugins:
            raise ValueError("Select a connected education source.")
        return [item for item in await providers.load(plugin_id) if not item.get("requires_approval")]

    @tool
    def read_education_context() -> dict[str, object]:
        """Read the original evidence, known children, and their current education snapshots."""
        review = store.education_review(review_id, family_id)
        if not review or not review["incoming"]:
            raise ValueError("The education review source is unavailable.")
        from app.auth import families
        children = json.loads(json.dumps([dict(child) for child in families.list_children(family_id)], default=str))
        return {
            "incoming": review["incoming"],
            "children": children,
            "snapshots": store.education_snapshots(family_id),
            "connected_sources": education_plugins,
        }

    @tool
    async def list_education_source_tools(plugin_id: str) -> list[dict[str, object]]:
        """List the read tools exposed by one connected Education-category plugin."""
        return await load_read_tools(plugin_id)

    @tool
    async def read_education_source(plugin_id: str, name: str, arguments: dict[str, object]) -> dict[str, object]:
        """Call an exact read tool from a connected Education-category plugin."""
        directory = await load_read_tools(plugin_id)
        if name not in {item["name"] for item in directory}:
            raise ValueError("Select an exact read tool returned by the education source.")
        return await providers.call(plugin_id, name, arguments, f"education-{review_id}-{name}")

    @tool
    def read_education_snapshot_skill() -> dict[str, object]:
        """Read the family's editable procedure for maintaining education snapshots."""
        from app.skills import BUILTIN_SKILLS
        store.seed_skills(family_id, BUILTIN_SKILLS)
        skill = next((item for item in store.skills(family_id) if item["slug"] == "education-snapshot-maintenance"), None)
        if not skill:
            raise ValueError("The Education Snapshot Maintenance skill is unavailable.")
        return {"name": skill["name"], "instructions": skill["instructions"]}

    @tool
    def update_education_snapshot(child_id: str, summary: str) -> dict[str, object]:
        """Replace one known child's living education snapshot with evidence-grounded natural language."""
        review = store.education_review(review_id, family_id)
        if not review or review["status"] != "processing":
            raise ValueError("This education review is not available for updates.")
        child = child_id.strip()
        clean_summary = summary.strip()
        from app.auth import families
        if not families.child(family_id, child):
            raise ValueError("The snapshot must belong to a known child.")
        if not clean_summary:
            raise ValueError("An education snapshot needs a natural-language summary.")
        store.update_education_snapshot(family_id, child, clean_summary, str(review["incoming_id"]))
        if child not in updated_children:
            updated_children.append(child)
        return {"status": "updated", "child_id": child}

    @tool
    def complete_education_review(reason: str) -> dict[str, object]:
        """Finish this review after recording every supported snapshot update."""
        clean_reason = reason.strip()
        if not clean_reason:
            raise ValueError("The education review needs an evidence-based reason.")
        review = store.education_review(review_id, family_id)
        if not review or review["status"] != "processing":
            raise ValueError("This education review is not available for completion.")
        action = "update" if updated_children else "ignore"
        store.set_education_review(review_id, status="completed", action=action, reason=clean_reason, failure="", processed_at=now())
        result.update(action=action, child_ids=list(updated_children))
        return {"status": "completed", **result}

    config = settings or get_settings()
    session = boto3.Session(profile_name=config.aws_profile or None, region_name=config.strands_region)
    agent = Agent(
        name="mom_life_education_agent",
        model=BedrockModel(boto_session=session, model_id=config.strands_model_id, temperature=0.1),
        system_prompt=EDUCATION_PROMPT,
        tools=[read_education_context, read_education_snapshot_skill, list_education_source_tools, read_education_source, update_education_snapshot, complete_education_review],
        hooks=[_StopAfterCompletion(result)],
        tool_executor=SequentialToolExecutor(),
        callback_handler=None,
    )
    stream = agent.stream_async(json.dumps({"family_id": family_id, "review_id": review_id}))
    try:
        async for _ in stream:
            if result:
                break
    finally:
        await stream.aclose()
        await providers.close()
    if not result:
        raise RuntimeError("The Education Agent stopped without completing its review.")
    return result
