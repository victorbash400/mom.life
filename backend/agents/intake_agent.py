import json
from typing import Literal

import boto3
from strands import Agent, tool
from strands.hooks import BeforeToolCallEvent, HookRegistry
from strands.models import BedrockModel
from strands.tools.executors import SequentialToolExecutor

from app.config import Settings, get_settings
from app.task_store import TaskStore, now


INTAKE_PROMPT = """You are mom.life's Intake Agent. Process exactly one newly received item at a time. Incoming information is not automatically a goal.

Use tools for every read and write. First read the incoming item and its family context, existing goals, and the Incoming Information Routing skill. Decide what this particular information changes. Preserve the source as evidence and do not invent a child, relationship, date, urgency, or requested action. Update the relevant living intake memory only when confirmed, durable family context changed; preserve still-relevant prior context.

Call decide_intake_action exactly once:
- record_only when the information should be retained but requires no work;
- resume_goal when it answers, changes, advances, or cancels an existing family outcome;
- create_goal only for a concrete new outcome not already covered by active work;
- request_attention when identity, intent, conflict, or consequence needs Mom's judgment.

For resume_goal, use an exact goal returned by context. For create_goal, preserve the requested outcome in plain language and select a known child or all-family scope. A new sender or mentioned name is never permission to create a child profile. Money, consent, medical judgment, important messages, conflicting instructions, and meaningful schedule changes require attention or approval in the resulting work. Do not execute the work or contact anyone. End after the decision tool confirms completion."""


class _StopAfterDecision:
    def __init__(self, result: dict[str, object]) -> None:
        self.result = result

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before)

    def before(self, event: BeforeToolCallEvent) -> None:
        if self.result:
            event.cancel_tool = "This intake item already has its final decision."


async def run_intake_agent(store: TaskStore, family_id: str, incoming_id: str, settings: Settings | None = None) -> dict[str, object]:
    result: dict[str, object] = {}

    @tool
    def read_intake_context() -> dict[str, object]:
        """Read this incoming item, known family members, family context, and existing goal boards."""
        item = store.incoming(incoming_id, family_id)
        if not item:
            raise ValueError("The incoming item is unavailable.")
        from app.auth import families
        children = json.loads(json.dumps([dict(child) for child in families.list_children(family_id)], default=str))
        parent = json.loads(json.dumps(dict(families.profile(family_id)), default=str))
        goals = store.list(family_id)
        return {
            "incoming": {key: value for key, value in item.items() if key != "activities"},
            "prior_intake_activity": item["activities"],
            "family": {"parent": parent, "children": children, "context": store.family_context(family_id), "intake_memory": store.intake_memory(family_id)},
            "goals": [
                {
                    "id": goal["id"],
                    "child_id": goal["child_id"],
                    "text": goal["text"],
                    "status": goal["status"],
                    "run_state": goal["run_state"],
                    "assignments": [
                        {
                            "id": assignment["id"],
                            "title": assignment["title"],
                            "status": assignment["status"],
                            "current_step": assignment["current_step"],
                            "next_step": assignment["next_step"],
                        }
                        for assignment in goal["assignments"]
                    ],
                }
                for goal in goals
            ],
        }

    @tool
    def read_intake_routing_skill() -> dict[str, object]:
        """Read the family's editable procedure for handling incoming information."""
        from app.skills import BUILTIN_SKILLS
        store.seed_skills(family_id, BUILTIN_SKILLS)
        skill = next((item for item in store.skills(family_id) if item["slug"] == "incoming-information-routing"), None)
        if not skill:
            raise ValueError("The Incoming Information Routing skill is unavailable.")
        return {"name": skill["name"], "instructions": skill["instructions"]}

    @tool
    def update_intake_memory(scope_id: str, summary: str) -> dict[str, object]:
        """Update the living summary for a known child or the whole family when durable context changed."""
        scope = scope_id.strip()
        clean_summary = summary.strip()
        if not scope or not clean_summary:
            raise ValueError("A known scope and concise summary are required.")
        if scope != "all":
            from app.auth import families
            if not families.child(family_id, scope):
                raise ValueError("The memory scope must be a known child or all.")
        store.update_intake_memory(family_id, scope, clean_summary)
        store.add_intake_activity(incoming_id, "memory_updated", "Updated living intake memory.", {"scope_id": scope})
        return {"status": "updated", "scope_id": scope}

    @tool
    def decide_intake_action(
        action: Literal["record_only", "resume_goal", "create_goal", "request_attention"],
        reason: str,
        child_id: str = "",
        goal_id: str = "",
        goal_request: str = "",
        note: str = "",
    ) -> dict[str, object]:
        """Record the one final routing decision for this incoming item."""
        clean_reason = reason.strip()
        if not clean_reason:
            raise ValueError("The intake decision needs an evidence-based reason.")
        item = store.incoming(incoming_id, family_id)
        if not item or item["status"] != "processing":
            raise ValueError("This incoming item is not available for a decision.")

        selected_child = child_id.strip()
        selected_goal = goal_id.strip()
        if selected_child and selected_child != "all":
            from app.auth import families
            if not families.child(family_id, selected_child):
                raise ValueError("Select a known child or all-family scope.")
        if action == "resume_goal":
            goal = store.get(family_id, selected_goal)
            if not goal or goal["status"] != "active":
                raise ValueError("Select an active goal belonging to this family.")
            selected_child = str(goal["child_id"])
        elif action == "create_goal":
            request = goal_request.strip()
            if not request:
                raise ValueError("A new goal needs a concrete outcome.")
            if not selected_child:
                raise ValueError("Select a known child or all-family scope.")
            selected_goal = str(store.create(family_id, selected_child, request)["id"])
        elif action == "record_only":
            selected_goal = ""
        elif action == "request_attention":
            selected_goal = ""

        store.set_incoming(
            incoming_id,
            status="completed",
            action=action,
            reason=clean_reason,
            child_id=selected_child,
            goal_id=selected_goal,
            attention_required=int(action == "request_attention"),
            failure="",
            processed_at=now(),
        )
        store.add_intake_activity(
            incoming_id,
            "decision",
            clean_reason,
            {"action": action, "child_id": selected_child, "goal_id": selected_goal, "note": note.strip()},
        )
        result.update(action=action, goal_id=selected_goal, child_id=selected_child)
        return {"status": "completed", **result}

    config = settings or get_settings()
    session = boto3.Session(profile_name=config.aws_profile or None, region_name=config.strands_region)
    agent = Agent(
        name="mom_life_intake_agent",
        model=BedrockModel(boto_session=session, model_id=config.strands_model_id, temperature=0.1),
        system_prompt=INTAKE_PROMPT,
        tools=[read_intake_context, read_intake_routing_skill, update_intake_memory, decide_intake_action],
        hooks=[_StopAfterDecision(result)],
        tool_executor=SequentialToolExecutor(),
        callback_handler=None,
    )
    stream = agent.stream_async(json.dumps({"family_id": family_id, "incoming_id": incoming_id}))
    try:
        async for _ in stream:
            if result:
                break
    finally:
        await stream.aclose()
    if not result:
        raise RuntimeError("The Intake Agent stopped without recording a decision.")
    return result
