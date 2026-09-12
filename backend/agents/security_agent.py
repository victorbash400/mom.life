import asyncio
import json
from typing import Literal

import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.executors import SequentialToolExecutor

from app.config import Settings, get_settings
from agents.invocation import invoke
from app.task_store import TaskStore, now


SECURITY_PROMPT = """You are mom.life's Safety Agent. Review exactly one incoming family item for a credible safety concern, including digital and physical safety. Do not route ordinary family work and do not execute a response.

Use tools for every read and write. First read the original item, family context, parent safety settings, and Family Safety Monitoring skill. Interpret the evidence in context; never use keyword matching and never invent identity, intent, location, urgency, or harm.

Follow the parent's alert level:
- urgent: alert only for an imminent or high-consequence credible concern;
- important: alert for a credible concern that needs the parent's awareness or decision;
- all: alert for any credible concern, including low-severity items.

The parent's free-form instructions refine those defaults. Call decide_security_action exactly once. Use ignore when the item does not cross the configured threshold. Use alert only when Mom should see a concise, evidence-grounded alert. Categories are descriptive, not a fixed taxonomy. End after the decision tool confirms completion."""


async def run_security_agent(store: TaskStore, family_id: str, review_id: str, settings: Settings | None = None) -> dict[str, object]:
    result: dict[str, object] = {}
    agent_ref: dict[str, Agent] = {}

    def security_context() -> dict[str, object]:
        review = store.security_review(review_id, family_id)
        if not review or not review["incoming"]:
            raise ValueError("The safety review source is unavailable.")
        from app.auth import families
        parent, children = families.snapshot(family_id)
        return {
            "review": {key: value for key, value in review.items() if key not in {"activities", "incoming"}},
            "incoming": review["incoming"],
            "settings": store.security_settings(family_id),
            "family": {
                "parent": json.loads(json.dumps(dict(parent), default=str)),
                "children": json.loads(json.dumps([dict(child) for child in children], default=str)),
            },
        }

    @tool
    async def read_security_context() -> dict[str, object]:
        """Read the original evidence, known family members, and saved parent safety settings."""
        return await asyncio.to_thread(security_context)

    @tool
    async def read_security_monitoring_skill() -> dict[str, object]:
        """Read the family's editable procedure for reviewing safety concerns."""
        def read():
            from app.skills import BUILTIN_SKILLS
            store.seed_skills(family_id, BUILTIN_SKILLS)
            return next((item for item in store.skills(family_id) if item["slug"] == "family-security-monitoring"), None)
        skill = await asyncio.to_thread(read)
        if not skill:
            raise ValueError("The Family Safety Monitoring skill is unavailable.")
        return {"name": skill["name"], "instructions": skill["instructions"]}

    @tool
    async def decide_security_action(
        action: Literal["ignore", "alert"],
        reason: str,
        severity: Literal["low", "moderate", "high", "critical"] = "low",
        category: str = "",
        summary: str = "",
        child_id: str = "",
    ) -> dict[str, object]:
        """Record the one final safety decision for this review."""
        clean_reason = reason.strip()
        if not clean_reason:
            raise ValueError("The safety decision needs an evidence-based reason.")
        selected_child = child_id.strip()
        clean_summary = summary.strip()
        if action == "alert" and not clean_summary:
            raise ValueError("A safety alert needs a concise summary.")
        def decide():
            review = store.security_review(review_id, family_id)
            if not review or review["status"] != "processing":
                raise ValueError("This safety review is not available for a decision.")
            if selected_child and selected_child != "all":
                from app.auth import families
                if not families.child(family_id, selected_child):
                    raise ValueError("Select a known child or all-family scope.")
            store.set_security_review(review_id, status="completed", action=action,
                severity=severity if action == "alert" else "", category=category.strip() if action == "alert" else "",
                summary=clean_summary if action == "alert" else "", reason=clean_reason,
                child_id=selected_child, failure="", processed_at=now())
            store.add_security_activity(review_id, "decision", clean_reason,
                {"action": action, "severity": severity, "category": category.strip(), "child_id": selected_child})
        await asyncio.to_thread(decide)
        result.update(action=action, severity=severity, child_id=selected_child)
        agent_ref["agent"].cancel()
        return {"status": "completed", **result}

    config = settings or get_settings()
    session = boto3.Session(profile_name=config.aws_profile or None, region_name=config.strands_region)
    agent = Agent(
        name="mom_life_safety_agent",
        model=BedrockModel(boto_session=session, model_id=config.strands_model_id, temperature=0.1, max_tokens=config.model_max_tokens, service_tier=config.model_service_tier),
        system_prompt=SECURITY_PROMPT,
        tools=[read_security_context, read_security_monitoring_skill, decide_security_action],
        tool_executor=SequentialToolExecutor(),
        callback_handler=None,
    )
    agent_ref["agent"] = agent
    await invoke(agent, json.dumps({"family_id": family_id, "review_id": review_id}), config.model_timeout_seconds)
    if not result:
        raise RuntimeError("The Safety Agent stopped without recording a decision.")
    return result
