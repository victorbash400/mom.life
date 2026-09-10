import asyncio
import json

import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.executors import SequentialToolExecutor

from app.config import Settings, get_settings
from agents.invocation import invoke
from app.task_store import TaskStore, now
from plugins.catalog import PLUGINS
from plugins.runtime import PluginToolSession


EDUCATION_PROMPT = """You are mom.life's Education Agent. Review exactly one incoming family item and keep each known child's education snapshot useful for Mom.

Use tools for every read and write. Read the original evidence, known children, existing snapshots, and the family's Education Snapshot Maintenance skill. Do not use keyword rules and do not invent a child, curriculum, subject, grade, ability, attendance figure, deadline, or result.

When confirmed information materially improves a known child's education picture, call update_education_snapshot with a complete natural-language snapshot that preserves still-relevant prior context. The snapshot should explain what the child is learning, how things appear to be going, meaningful changes, and anything important for Mom to know. It may be as short or detailed as the evidence warrants. Update every affected known child, and never force unrelated information into a snapshot.

Call complete_education_review exactly once after any updates, or immediately when the item adds nothing useful. Do not create tasks, contact anyone, or make education decisions. End after completion is confirmed."""


async def run_education_agent(store: TaskStore, family_id: str, review_id: str, settings: Settings | None = None) -> dict[str, object]:
    result: dict[str, object] = {}
    agent_ref: dict[str, Agent] = {}
    updated_children: list[str] = []
    def connected_plugins():
        with store._connect() as connection:
            return {row["plugin_id"] for row in connection.execute("SELECT plugin_id FROM plugin_connections WHERE family_id=?", (family_id,)).fetchall()}
    connected = await asyncio.to_thread(connected_plugins)
    education_plugins = [plugin.id for plugin in PLUGINS if plugin.group == "Education" and plugin.id in connected]
    providers = PluginToolSession(education_plugins, store, family_id)

    async def load_read_tools(plugin_id: str) -> list[dict[str, object]]:
        if plugin_id not in education_plugins:
            raise ValueError("Select a connected education source.")
        return [item for item in await providers.load(plugin_id) if not item.get("requires_approval")]

    @tool
    async def read_education_context() -> dict[str, object]:
        """Read the original evidence, known children, and their current education snapshots."""
        def read():
            review = store.education_review(review_id, family_id)
            if not review or not review["incoming"]:
                raise ValueError("The education review source is unavailable.")
            from app.auth import families
            children = json.loads(json.dumps([dict(child) for child in families.list_children(family_id)], default=str))
            return {"incoming": review["incoming"], "children": children,
                "snapshots": store.education_snapshots(family_id), "connected_sources": education_plugins}
        return await asyncio.to_thread(read)

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
    async def read_education_snapshot_skill() -> dict[str, object]:
        """Read the family's editable procedure for maintaining education snapshots."""
        def read():
            from app.skills import BUILTIN_SKILLS
            store.seed_skills(family_id, BUILTIN_SKILLS)
            return next((item for item in store.skills(family_id) if item["slug"] == "education-snapshot-maintenance"), None)
        skill = await asyncio.to_thread(read)
        if not skill:
            raise ValueError("The Education Snapshot Maintenance skill is unavailable.")
        return {"name": skill["name"], "instructions": skill["instructions"]}

    @tool
    async def update_education_snapshot(child_id: str, summary: str) -> dict[str, object]:
        """Replace one known child's living education snapshot with evidence-grounded natural language."""
        child = child_id.strip()
        clean_summary = summary.strip()
        if not clean_summary:
            raise ValueError("An education snapshot needs a natural-language summary.")
        def update():
            review = store.education_review(review_id, family_id)
            if not review or review["status"] != "processing":
                raise ValueError("This education review is not available for updates.")
            from app.auth import families
            if not families.child(family_id, child):
                raise ValueError("The snapshot must belong to a known child.")
            store.update_education_snapshot(family_id, child, clean_summary, str(review["incoming_id"]))
        await asyncio.to_thread(update)
        if child not in updated_children:
            updated_children.append(child)
        return {"status": "updated", "child_id": child}

    @tool
    async def complete_education_review(reason: str) -> dict[str, object]:
        """Finish this review after recording every supported snapshot update."""
        clean_reason = reason.strip()
        if not clean_reason:
            raise ValueError("The education review needs an evidence-based reason.")
        action = "update" if updated_children else "ignore"
        def complete():
            review = store.education_review(review_id, family_id)
            if not review or review["status"] != "processing":
                raise ValueError("This education review is not available for completion.")
            store.set_education_review(review_id, status="completed", action=action, reason=clean_reason, failure="", processed_at=now())
        await asyncio.to_thread(complete)
        result.update(action=action, child_ids=list(updated_children))
        agent_ref["agent"].cancel()
        return {"status": "completed", **result}

    config = settings or get_settings()
    session = boto3.Session(profile_name=config.aws_profile or None, region_name=config.strands_region)
    agent = Agent(
        name="mom_life_education_agent",
        model=BedrockModel(boto_session=session, model_id=config.strands_model_id, temperature=0.1, max_tokens=config.model_max_tokens, service_tier=config.model_service_tier),
        system_prompt=EDUCATION_PROMPT,
        tools=[read_education_context, read_education_snapshot_skill, list_education_source_tools, read_education_source, update_education_snapshot, complete_education_review],
        tool_executor=SequentialToolExecutor(),
        callback_handler=None,
    )
    agent_ref["agent"] = agent
    try:
        await invoke(agent, json.dumps({"family_id": family_id, "review_id": review_id}), config.model_timeout_seconds)
    finally:
        await providers.close()
    if not result:
        raise RuntimeError("The Education Agent stopped without completing its review.")
    return result
