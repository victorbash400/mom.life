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


INTAKE_PROMPT = """You are mom.life's Intake Agent. Process exactly one newly received item at a time. Incoming information is not automatically a goal.

Use tools for every read and write. First read the incoming item and its family context, existing goals, and the Incoming Information Routing skill. Decide what this particular information changes. Preserve the source as evidence and do not invent a child, relationship, date, urgency, or requested action. Update the relevant living intake memory only when confirmed, durable family context changed; preserve still-relevant prior context.

Call decide_intake_action exactly once:
- record_only when the information should be retained but requires no work;
- resume_goal when it answers, changes, advances, or cancels an existing family outcome;
- create_goal only for a concrete new outcome not already covered by active work;
- request_attention when identity, intent, conflict, or consequence needs Mom's judgment.

For resume_goal, use an exact goal returned by context. For create_goal, preserve the requested outcome in plain language and select a known child or all-family scope. A new sender or mentioned name is never permission to create a child profile. Request Mom's attention only when consequential information needs a choice she has not already made, such as an unrequested payment, consent decision, medical judgment, conflicting instruction, or ambiguous schedule change. Do not execute the work or contact anyone. End after the decision tool confirms completion."""


async def run_intake_agent(store: TaskStore, family_id: str, incoming_id: str, settings: Settings | None = None) -> dict[str, object]:
    result: dict[str, object] = {}
    agent_ref: dict[str, Agent] = {}

    def intake_context() -> dict[str, object]:
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
    async def read_intake_context() -> dict[str, object]:
        """Read this incoming item, known family members, family context, and existing goal boards."""
        return await asyncio.to_thread(intake_context)

    @tool
    async def read_intake_routing_skill() -> dict[str, object]:
        """Read the family's editable procedure for handling incoming information."""
        def read():
            from app.skills import BUILTIN_SKILLS
            store.seed_skills(family_id, BUILTIN_SKILLS)
            return next((item for item in store.skills(family_id) if item["slug"] == "incoming-information-routing"), None)
        skill = await asyncio.to_thread(read)
        if not skill:
            raise ValueError("The Incoming Information Routing skill is unavailable.")
        return {"name": skill["name"], "instructions": skill["instructions"]}

    @tool
    async def update_intake_memory(scope_id: str, summary: str) -> dict[str, object]:
        """Update the living summary for a known child or the whole family when durable context changed."""
        scope = scope_id.strip()
        clean_summary = summary.strip()
        if not scope or not clean_summary:
            raise ValueError("A known scope and concise summary are required.")
        def update():
            if scope != "all":
                from app.auth import families
                if not families.child(family_id, scope):
                    raise ValueError("The memory scope must be a known child or all.")
            store.update_intake_memory(family_id, scope, clean_summary)
            store.add_intake_activity(incoming_id, "memory_updated", "Updated living intake memory.", {"scope_id": scope})
        await asyncio.to_thread(update)
        return {"status": "updated", "scope_id": scope}

    @tool
    async def decide_intake_action(
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
        selected_child = child_id.strip()
        selected_goal = goal_id.strip()
        def decide() -> tuple[str, str]:
            item = store.incoming(incoming_id, family_id)
            if not item or item["status"] != "processing":
                raise ValueError("This incoming item is not available for a decision.")
            child = selected_child
            goal_identity = selected_goal
            if child and child != "all":
                from app.auth import families
                if not families.child(family_id, child):
                    raise ValueError("Select a known child or all-family scope.")
            if action == "resume_goal":
                goal = store.get(family_id, goal_identity)
                if not goal or goal["status"] != "active":
                    raise ValueError("Select an active goal belonging to this family.")
                child = str(goal["child_id"])
            elif action == "create_goal":
                request = goal_request.strip()
                if not request:
                    raise ValueError("A new goal needs a concrete outcome.")
                if not child:
                    raise ValueError("Select a known child or all-family scope.")
                goal_identity = str(store.create(family_id, child, request)["id"])
            else:
                goal_identity = ""
            if goal_identity:
                store.add_activity(goal_identity, "intake_source", clean_reason, {
                    "incoming_id": incoming_id, "source": item["source"],
                    "provider_event_id": item["provider_event_id"], "sender": item["sender"],
                    "subject": item["subject"], "content": item["content"],
                })
            store.set_incoming(incoming_id, status="completed", action=action, reason=clean_reason,
                child_id=child, goal_id=goal_identity, attention_required=int(action == "request_attention"),
                failure="", processed_at=now())
            store.add_intake_activity(incoming_id, "decision", clean_reason,
                {"action": action, "child_id": child, "goal_id": goal_identity, "note": note.strip()})
            return child, goal_identity
        selected_child, selected_goal = await asyncio.to_thread(decide)
        result.update(action=action, goal_id=selected_goal, child_id=selected_child)
        agent_ref["agent"].cancel()
        return {"status": "completed", **result}

    config = settings or get_settings()
    session = boto3.Session(profile_name=config.aws_profile or None, region_name=config.strands_region)
    agent = Agent(
        name="mom_life_intake_agent",
        model=BedrockModel(boto_session=session, model_id=config.strands_model_id, temperature=0.1, max_tokens=config.model_max_tokens, service_tier=config.model_service_tier),
        system_prompt=INTAKE_PROMPT,
        tools=[read_intake_context, read_intake_routing_skill, update_intake_memory, decide_intake_action],
        tool_executor=SequentialToolExecutor(),
        callback_handler=None,
    )
    agent_ref["agent"] = agent
    await invoke(agent, json.dumps({"family_id": family_id, "incoming_id": incoming_id}), config.model_timeout_seconds)
    if not result:
        raise RuntimeError("The Intake Agent stopped without recording a decision.")
    return result
