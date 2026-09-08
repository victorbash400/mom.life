import json
from typing import Literal

import boto3
from strands import Agent, tool
from strands.hooks import BeforeToolCallEvent, HookRegistry
from strands.models import BedrockModel
from strands.tools.executors import SequentialToolExecutor

from app.config import Settings, get_settings
from app.task_store import TaskStore, now


SECURITY_PROMPT = """You are mom.life's Security Agent. Review exactly one incoming family item for a credible security or safety concern. Do not route ordinary family work and do not execute a response.

Use tools for every read and write. First read the original item, family context, parent security settings, and Family Security Monitoring skill. Interpret the evidence in context; never use keyword matching and never invent identity, intent, location, urgency, or harm.

Follow the parent's alert level:
- urgent: alert only for an imminent or high-consequence credible concern;
- important: alert for a credible concern that needs the parent's awareness or decision;
- all: alert for any credible concern, including low-severity items.

The parent's free-form instructions refine those defaults. Call decide_security_action exactly once. Use ignore when the item does not cross the configured threshold. Use alert only when Mom should see a concise, evidence-grounded alert. Categories are descriptive, not a fixed taxonomy. End after the decision tool confirms completion."""


class _StopAfterDecision:
    def __init__(self, result: dict[str, object]) -> None:
        self.result = result

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before)

    def before(self, event: BeforeToolCallEvent) -> None:
        if self.result:
            event.cancel_tool = "This security review already has its final decision."


async def run_security_agent(store: TaskStore, family_id: str, review_id: str, settings: Settings | None = None) -> dict[str, object]:
    result: dict[str, object] = {}

    @tool
    def read_security_context() -> dict[str, object]:
        """Read the original evidence, known family members, and saved parent security settings."""
        review = store.security_review(review_id, family_id)
        if not review or not review["incoming"]:
            raise ValueError("The security review source is unavailable.")
        from app.auth import families
        return {
            "review": {key: value for key, value in review.items() if key not in {"activities", "incoming"}},
            "incoming": review["incoming"],
            "settings": store.security_settings(family_id),
            "family": {
                "parent": json.loads(json.dumps(dict(families.profile(family_id)), default=str)),
                "children": json.loads(json.dumps([dict(child) for child in families.list_children(family_id)], default=str)),
                "context": store.family_context(family_id),
            },
        }

    @tool
    def read_security_monitoring_skill() -> dict[str, object]:
        """Read the family's editable procedure for reviewing security concerns."""
        from app.skills import BUILTIN_SKILLS
        store.seed_skills(family_id, BUILTIN_SKILLS)
        skill = next((item for item in store.skills(family_id) if item["slug"] == "family-security-monitoring"), None)
        if not skill:
            raise ValueError("The Family Security Monitoring skill is unavailable.")
        return {"name": skill["name"], "instructions": skill["instructions"]}

    @tool
    def decide_security_action(
        action: Literal["ignore", "alert"],
        reason: str,
        severity: Literal["low", "moderate", "high", "critical"] = "low",
        category: str = "",
        summary: str = "",
        child_id: str = "",
    ) -> dict[str, object]:
        """Record the one final security decision for this review."""
        clean_reason = reason.strip()
        if not clean_reason:
            raise ValueError("The security decision needs an evidence-based reason.")
        review = store.security_review(review_id, family_id)
        if not review or review["status"] != "processing":
            raise ValueError("This security review is not available for a decision.")
        selected_child = child_id.strip()
        if selected_child and selected_child != "all":
            from app.auth import families
            if not families.child(family_id, selected_child):
                raise ValueError("Select a known child or all-family scope.")
        clean_summary = summary.strip()
        if action == "alert" and not clean_summary:
            raise ValueError("A security alert needs a concise summary.")
        store.set_security_review(
            review_id,
            status="completed",
            action=action,
            severity=severity if action == "alert" else "",
            category=category.strip() if action == "alert" else "",
            summary=clean_summary if action == "alert" else "",
            reason=clean_reason,
            child_id=selected_child,
            failure="",
            processed_at=now(),
        )
        store.add_security_activity(
            review_id,
            "decision",
            clean_reason,
            {"action": action, "severity": severity, "category": category.strip(), "child_id": selected_child},
        )
        result.update(action=action, severity=severity, child_id=selected_child)
        return {"status": "completed", **result}

    config = settings or get_settings()
    session = boto3.Session(profile_name=config.aws_profile or None, region_name=config.strands_region)
    agent = Agent(
        name="mom_life_security_agent",
        model=BedrockModel(boto_session=session, model_id=config.strands_model_id, temperature=0.1),
        system_prompt=SECURITY_PROMPT,
        tools=[read_security_context, read_security_monitoring_skill, decide_security_action],
        hooks=[_StopAfterDecision(result)],
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
    if not result:
        raise RuntimeError("The Security Agent stopped without recording a decision.")
    return result
