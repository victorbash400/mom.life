"""Amazon Bedrock AgentCore Runtime entrypoint for mom.life's Strands agents."""
import asyncio
import json
import os

import boto3


def _load_config_secret() -> None:
    secret_arn = os.environ.get("MOM_LIFE_CONFIG_SECRET_ARN", "")
    if not secret_arn:
        return
    response = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1")).get_secret_value(SecretId=secret_arn)
    values = json.loads(response["SecretString"])
    if not isinstance(values, dict):
        raise RuntimeError("The mom.life configuration secret must contain a JSON object.")
    for key, value in values.items():
        if isinstance(key, str) and isinstance(value, str):
            os.environ.setdefault(key, value)


_load_config_secret()

from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

from agents.education_agent import run_education_agent
from agents.goal_planner import plan_goal
from agents.goal_worker import run_worker
from agents.intake_agent import run_intake_agent
from agents.mom_life_agent import ToolEventRecorder, create_mom_life_agent
from agents.security_agent import run_security_agent
from app.config import get_settings
from app.task_store import TaskStore
from plugins.runtime import PluginToolSession


app = BedrockAgentCoreApp()


def _required(payload: dict, name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required.")
    return value.strip()


def _local_settings():
    return get_settings().model_copy(update={"agentcore_runtime_arn": "", "aws_profile": ""})


def _store() -> TaskStore:
    settings = _local_settings()
    if not settings.database_url:
        raise RuntimeError("MOM_LIFE_DATABASE_URL is required.")
    return TaskStore(settings.database_url)


async def _chat(payload: dict):
    settings = _local_settings()
    family_id = _required(payload, "family_id")
    chat_id = _required(payload, "chat_id")
    message = _required(payload, "message")
    if not settings.agentcore_memory_id:
        raise RuntimeError("MOM_LIFE_AGENTCORE_MEMORY_ID is required.")
    manager = AgentCoreMemorySessionManager(
        AgentCoreMemoryConfig(
            memory_id=settings.agentcore_memory_id,
            actor_id=family_id,
            session_id=chat_id,
            async_mode=True,
        ),
        region_name=settings.strands_region,
    )
    tool_events = ToolEventRecorder()
    seen_tools: set[str] = set()
    try:
        agent = create_mom_life_agent(
            chat_id,
            tool_events,
            settings=settings,
            family_id=family_id,
            session_manager=manager,
        )
        async for event in agent.stream_async(message):
            for completed in tool_events.drain():
                yield {"type": "tool_response", **completed}
            content = event.get("data")
            if isinstance(content, str) and content:
                yield {"type": "content", "content": content}
            tool_use = event.get("current_tool_use")
            if (
                isinstance(tool_use, dict)
                and tool_use.get("toolUseId")
                and tool_use.get("name")
                and tool_use["toolUseId"] not in seen_tools
            ):
                seen_tools.add(tool_use["toolUseId"])
                yield {
                    "type": "tool_call",
                    "id": str(tool_use["toolUseId"]),
                    "name": str(tool_use["name"]),
                    "args": tool_use.get("input") if isinstance(tool_use.get("input"), dict) else {},
                }
        for completed in tool_events.drain():
            yield {"type": "tool_response", **completed}
        yield {"type": "done"}
    finally:
        manager.close()


async def _work(payload: dict, on_progress=None):
    store = _store()
    family_id = _required(payload, "family_id")
    child_id = _required(payload, "child_id")
    goal_id = _required(payload, "goal_id")
    assignment_id = _required(payload, "assignment_id")
    prompt = _required(payload, "prompt")
    plugin_ids = payload.get("plugin_ids")
    expected_outputs = payload.get("expected_outputs")
    if not isinstance(plugin_ids, list) or not all(isinstance(item, str) for item in plugin_ids):
        raise ValueError("plugin_ids must be a list of strings.")
    if not isinstance(expected_outputs, list) or not all(isinstance(item, str) for item in expected_outputs):
        raise ValueError("expected_outputs must be a list of strings.")

    def progress(message: str, percent: int, next_step: str) -> None:
        store.set_assignment(assignment_id, current_step=message, progress=percent, next_step=next_step)
        store.set_goal_state(goal_id, current_step=message, progress=percent)
        store.add_activity(goal_id, "worker_update", message, {"assignment_id": assignment_id, "next_step": next_step})
        if on_progress is not None:
            on_progress({"type": "progress", "assignment_id": assignment_id})

    plugins = PluginToolSession(plugin_ids, store, family_id, child_id)
    plugins.assignment_id = assignment_id
    try:
        result = await run_worker(
            prompt,
            plugins,
            progress,
            expected_outputs,
            store,
            goal_id,
            assignment_id,
            settings=_local_settings(),
        )
        plugins.preserve_browser = result.get("status") == "blocked" and not result.get("external_wait")
        return result
    finally:
        await plugins.close()


async def _result(payload: dict) -> dict:
    operation = _required(payload, "operation")
    settings = _local_settings()
    if operation == "plan":
        plan = await plan_goal(
            _required(payload, "request"),
            _required(payload, "child_id"),
            payload.get("skills") if isinstance(payload.get("skills"), list) else [],
            settings=settings,
            existing_tasks=payload.get("existing_tasks") if isinstance(payload.get("existing_tasks"), list) else [],
            plugins=payload.get("plugins") if isinstance(payload.get("plugins"), list) else [],
        )
        return plan.model_dump()
    if operation == "work":
        return await _work(payload)
    store = _store()
    family_id = _required(payload, "family_id")
    if operation == "intake":
        return await run_intake_agent(store, family_id, _required(payload, "incoming_id"), settings=settings)
    if operation == "security":
        return await run_security_agent(store, family_id, _required(payload, "review_id"), settings=settings)
    if operation == "education":
        return await run_education_agent(store, family_id, _required(payload, "review_id"), settings=settings)
    raise ValueError(f"Unsupported operation: {operation}")


@app.entrypoint
async def invoke(payload: dict):
    try:
        if payload.get("operation") == "chat":
            async for event in _chat(payload):
                yield event
            return
        if payload.get("operation") == "work":
            queue = asyncio.Queue()
            loop = asyncio.get_running_loop()
            worker = asyncio.create_task(_work(payload, lambda event: loop.call_soon_threadsafe(queue.put_nowait, event)))
            worker.add_done_callback(lambda done: queue.put_nowait(None))
            try:
                while (event := await queue.get()) is not None:
                    yield event
                yield {"type": "result", "result": await worker}
            finally:
                if not worker.done():
                    worker.cancel()
                await asyncio.gather(worker, return_exceptions=True)
            return
        yield {"type": "result", "result": await _result(payload)}
    except Exception as error:
        yield {"type": "error", "error": str(error).strip() or type(error).__name__}


if __name__ == "__main__":
    app.run()
