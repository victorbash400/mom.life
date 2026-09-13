import asyncio
import json
from collections.abc import AsyncIterator

from agents.agentcore_client import AgentCoreClient, runtime_session_id
from agents.mom_life_agent import ToolEventRecorder, create_mom_life_agent
from app.config import get_settings


_session_locks: dict[str, asyncio.Lock] = {}


async def stream_agent_events(*, family_id: str, chat_id: str, message: str) -> AsyncIterator[str]:
    from app.chat_routes import chats
    config = get_settings()
    session = chats.ensure(family_id, chat_id)
    session_id = chat_id if config.uses_agentcore_runtime else session.session_id
    lock = _session_locks.setdefault(session_id, asyncio.Lock())
    async with lock:
        if config.uses_agentcore_runtime:
            try:
                await asyncio.to_thread(chats.touch, family_id, chat_id, message)
                async for event in AgentCoreClient(config).events(
                    "chat",
                    {"family_id": family_id, "chat_id": chat_id, "message": message},
                    session_id=runtime_session_id("chat", family_id, chat_id),
                ):
                    yield _sse(event)
            except Exception as error:
                yield _sse({"type": "error", "error": str(error)})
            return
        tool_events = ToolEventRecorder()
        seen_tools: set[str] = set()
        try:
            agent = create_mom_life_agent(session_id, tool_events, family_id=family_id, session_manager=session)
            async for event in agent.stream_async(message):
                for completed in tool_events.drain():
                    yield _sse({"type": "tool_response", **completed})
                content = event.get("data")
                if isinstance(content, str) and content:
                    yield _sse({"type": "content", "content": content})
                tool_use = event.get("current_tool_use")
                if isinstance(tool_use, dict) and tool_use.get("toolUseId") and tool_use.get("name") and tool_use["toolUseId"] not in seen_tools:
                    seen_tools.add(tool_use["toolUseId"])
                    yield _sse({
                        "type": "tool_call",
                        "id": str(tool_use["toolUseId"]),
                        "name": str(tool_use.get("name") or "tool"),
                        "args": tool_use.get("input") if isinstance(tool_use.get("input"), dict) else {},
                    })
            for completed in tool_events.drain():
                yield _sse({"type": "tool_response", **completed})
            yield _sse({"type": "done"})
        except Exception as error:
            yield _sse({"type": "error", "error": str(error)})


def _sse(event: dict[str, object]) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"
