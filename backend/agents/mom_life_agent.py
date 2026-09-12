from pathlib import Path

import boto3
from strands import Agent
from strands.hooks import AfterToolCallEvent, HookRegistry
from strands.models import BedrockModel
from strands.session.file_session_manager import FileSessionManager

from app.config import Settings, get_settings
from tools.family_tools import get_current_datetime


SESSION_DIRECTORY = Path(__file__).resolve().parents[1] / ".sessions"
SYSTEM_PROMPT = """You are mom.life, the quiet operating layer for motherhood.
You are also a capable general assistant. Answer ordinary questions directly, including general knowledge,
explanations, writing, ideas, and casual conversation. Do not refuse or redirect a question merely because it is
unrelated to family management. Do not introduce yourself with a feature menu. Respond naturally, warmly, and
concisely; if the user is frustrated, ignore the hostility and answer the underlying request without scolding them.
Turn unstructured family information into clear, practical next steps while preserving who each detail concerns.
Handle safe and reversible organization quietly. Ask before money, consent, medical judgment, important messages,
or meaningful schedule changes. Escalate urgent, contradictory, or low-confidence situations clearly.
Never invent facts about a child. Distinguish confirmed information from assumptions.
Before your first tool call in each user turn, stream one brief, natural sentence explaining what you are about to check or do for this request. Never begin a turn with a tool call. Write the commentary in your own words, specific to the requested action; do not use a fixed phrase or repeat the same sentence across requests. Keep it short and do not claim success before the tool returns. For a new stage of work, give another brief update only when it helps explain the next action.
Use family tools only when the request needs family data or action. Read list_goal_tasks before reporting current work. Use create_family_goal for requested durable work and revise_goal_plan for every change to an existing board. The planner decides the assignments; do not invent fixed worker roles. Never claim a change without a successful tool result. Read get_family_context for child identity.
Use get_current_datetime whenever dates, deadlines, or relative time matter.
"""


class ToolEventRecorder:
    def __init__(self) -> None:
        self._completed: list[dict[str, str]] = []

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(AfterToolCallEvent, self.after_tool_call)

    def after_tool_call(self, event: AfterToolCallEvent) -> None:
        self._completed.append({
            "id": str(event.tool_use.get("toolUseId") or ""),
            "name": str(event.tool_use.get("name") or "tool"),
            "status": "error" if event.exception or event.result.get("status") == "error" else "done",
        })

    def drain(self) -> list[dict[str, str]]:
        completed, self._completed = self._completed, []
        return completed


def create_mom_life_agent(session_id: str, tool_events: ToolEventRecorder | None = None, settings: Settings | None = None, family_id: str | None = None, session_manager=None) -> Agent:
    from tools.goal_supervisor import supervisor_tools
    config = settings or get_settings()
    SESSION_DIRECTORY.mkdir(parents=True, exist_ok=True)
    boto_session = boto3.Session(profile_name=config.aws_profile or None, region_name=config.strands_region)
    return Agent(
        agent_id="mom-life",
        callback_handler=None,
        hooks=[tool_events] if tool_events else None,
        model=BedrockModel(boto_session=boto_session, model_id=config.strands_model_id, temperature=0.2, max_tokens=config.model_max_tokens, service_tier=config.model_service_tier),
        name="mom.life",
        session_manager=session_manager or FileSessionManager(session_id=session_id, storage_dir=str(SESSION_DIRECTORY)),
        system_prompt=SYSTEM_PROMPT,
        tools=[get_current_datetime, *(supervisor_tools(family_id) if family_id else [])],
    )
