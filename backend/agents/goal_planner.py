import json
from typing import Literal

import boto3
from pydantic import BaseModel, Field
from strands import Agent
from strands.models import BedrockModel

from app.config import Settings, get_settings


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


class GoalPlan(BaseModel):
    operations: list[AssignmentPlan] = Field(min_length=1)


PLANNER_PROMPT = """You are mom.life's goal planner. Convert one family outcome into the smallest strictly sequential assignment board needed to finish it. Workers are constructed from assignments; there are no fixed worker roles.

Keep research together with the action that consumes it. Split work only when a later assignment requires a separately verifiable output from an earlier assignment. Select only listed skills whose available field is true. When connection_setup_required is nonempty, preserve the requested outcome and instruct the worker to request missing access; do not invent an alternative outcome. Never invent a plugin, fact, person, date, recipient, or identifier. Preserve the request's wording and child scope.

Every assignment needs a complete operational instruction and exact, observable expected outputs. Money, consent, medical judgment, important messages, irreversible submissions, and meaningful schedule changes must be prepared and presented for Mom's approval before action. Read the existing task ledger first. Create, reuse, update, steer, retry, or cancel assignments. Preserve completed work and task identity. Retry the same failed task with a corrected instruction informed by its failure evidence. Do not create duplicate outcomes. Each create needs a unique key; dependencies reference earlier keys or existing task IDs. Keep unrelated assignments independent. Revision instructions must be complete. Return only the structured plan."""


async def plan_goal(request: str, child_id: str, skills: list[dict[str, object]], settings: Settings | None = None, existing_tasks: list[dict] | None = None) -> GoalPlan:
    config = settings or get_settings()
    session = boto3.Session(profile_name=config.aws_profile or None, region_name=config.strands_region)
    agent = Agent(
        name="mom_life_goal_planner",
        model=BedrockModel(boto_session=session, model_id=config.strands_model_id, temperature=0.1),
        system_prompt=PLANNER_PROMPT,
        structured_output_model=GoalPlan,
        callback_handler=None,
    )
    result = await agent.invoke_async(json.dumps({"request": request, "child_id": child_id, "available_skills": skills, "task_ledger": existing_tasks or []}))
    if not isinstance(result.structured_output, GoalPlan):
        raise RuntimeError("The goal planner did not return a valid assignment plan.")
    return result.structured_output
