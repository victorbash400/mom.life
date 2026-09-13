import json
import re
from typing import Literal

import boto3
from pydantic import BaseModel, Field
from strands import Agent
from agents.model import FamilyBedrockModel as BedrockModel

from app.config import Settings, get_settings
from agents.agentcore_client import AgentCoreClient, runtime_session_id
from agents.invocation import invoke


class AssignmentPlan(BaseModel):
    action: Literal["create", "reuse", "update", "steer", "retry", "cancel"]
    task_id: str = ""
    key: str = ""
    title: str = ""
    instruction: str = ""
    depends_on: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    skill_ids: list[str] = Field(default_factory=list)
    plugin_ids: list[str] = Field(default_factory=list)


class GoalPlan(BaseModel):
    operations: list[AssignmentPlan] = Field(min_length=1)


PLANNER_PROMPT = """You are mom.life's goal planner. Convert one family outcome into the smallest strictly sequential assignment board needed to finish it. Workers are constructed from assignments; there are no fixed worker roles.

Keep research together with the action that consumes it. Split work only when a later assignment requires a separately verifiable output from an earlier assignment. Select only listed skills whose available field is true. Select exact plugin_ids from available_plugins for every tool the assignment needs, including later automation actions. Respect the requested provider; never replace Fitbit with Apple Health or omit a requested messaging tool. Skills provide procedures, and plugin_ids provide tool access independently. When a required connection is unavailable, preserve the requested outcome and instruct the worker to request missing access; do not invent an alternative outcome. Never invent a plugin, fact, person, date, recipient, or identifier. Preserve the request's wording and child scope.

For monitoring or delayed work, create an assignment to save the automation and any requested baseline. Put the future check and action in the automation instruction, not in another assignment that would execute immediately. Include the known baseline and exact notification condition in the saved instruction. An automation check invocation executes the current check only; it must not create another automation or schedule itself again.

Keep sending a question, waiting for its reply, and acting on that reply in one assignment so the message receipt and reply correlation stay together. Include the messaging plugin for the entire assignment. The worker receives the current goal and assignment IDs; never request these internal identifiers from Mom.
Before returning, compare the entire request against the board. Every requested action must appear in an operational instruction and an observable expected output. Do not omit follow-up recipients or actions, or treat receiving a reply as completion when the request also requires acting on it.

Every assignment needs a complete operational instruction and exact, observable expected outputs. When the request gives an exact output name, preserve that label verbatim; never expand, explain, or rename it. The user's requested outcome and constraints are the authorization for that work. Ask Mom only when a necessary choice, identity, recipient, amount, consent decision, medical judgment, or other consequential detail is genuinely missing or ambiguous. Read the existing task ledger first. Create, reuse, update, steer, retry, or cancel assignments. Preserve completed work and task identity. Retry the same failed task with a corrected instruction informed by its failure evidence. Do not create duplicate outcomes. Each create needs a unique key; dependencies reference earlier keys or existing task IDs. Keep unrelated assignments independent. Revision instructions must be complete. Return only the structured plan."""


async def plan_goal(request: str, child_id: str, skills: list[dict[str, object]], settings: Settings | None = None, existing_tasks: list[dict] | None = None, plugins: list[dict] | None = None) -> GoalPlan:
    config = settings or get_settings()
    if config.uses_agentcore_runtime:
        payload = {
            "request": request,
            "child_id": child_id,
            "skills": skills,
            "existing_tasks": existing_tasks or [],
            "plugins": plugins or [],
        }
        result = await AgentCoreClient(config).result(
            "plan",
            payload,
            session_id=runtime_session_id("plan", child_id, request),
        )
        plan = GoalPlan.model_validate(result)
        _preserve_requested_output_labels(request, plan)
        return plan
    session = boto3.Session(profile_name=config.aws_profile or None, region_name=config.strands_region)
    agent = Agent(
        name="mom_life_goal_planner",
        model=BedrockModel(boto_session=session, model_id=config.strands_model_id, temperature=0.1, max_tokens=config.model_max_tokens, service_tier=config.model_service_tier, additional_request_fields=config.model_request_fields),
        system_prompt=PLANNER_PROMPT,
        structured_output_model=GoalPlan,
        callback_handler=None,
    )
    result = await invoke(agent, json.dumps({"request": request, "child_id": child_id, "available_skills": skills, "available_plugins": plugins or [], "task_ledger": existing_tasks or []}), config.model_timeout_seconds)
    if not isinstance(result.structured_output, GoalPlan):
        raise RuntimeError("The goal planner did not return a valid assignment plan.")
    _preserve_requested_output_labels(request, result.structured_output)
    return result.structured_output


def _preserve_requested_output_labels(request: str, plan: GoalPlan) -> None:
    labels = []
    for match in re.finditer(r"\boutputs?\s+named(?:\s+exactly)?\s+([^\n.]+)", request, re.IGNORECASE):
        segment = match.group(1).strip()
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", segment)
        values = quoted or [segment.strip(" '\"")]
        labels.extend(value for value in values if value)
    for label in dict.fromkeys(labels):
        exact = any(label in operation.expected_outputs for operation in plan.operations)
        if exact:
            continue
        for operation in plan.operations:
            for index, output in enumerate(operation.expected_outputs):
                if output.casefold().startswith(label.casefold()):
                    operation.expected_outputs[index] = label
                    break
            else:
                continue
            break
        else:
            words = set(re.findall(r"[a-z0-9]+", label.casefold()))
            target = max(
                plan.operations,
                key=lambda operation: len(words & set(re.findall(r"[a-z0-9]+", f"{operation.title} {operation.instruction}".casefold()))),
            )
            target.expected_outputs.append(label)
