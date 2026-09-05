import asyncio
import hashlib
import json
from collections.abc import AsyncIterator

from agents.mom_life_agent import ToolEventRecorder, create_mom_life_agent


_session_locks: dict[str, asyncio.Lock] = {}


async def stream_agent_events(*, family_id: str, chat_id: str, message: str) -> AsyncIterator[str]:
    session_id = hashlib.sha256(f"{family_id}:{chat_id}".encode()).hexdigest()
    lock = _session_locks.setdefault(session_id, asyncio.Lock())
    async with lock:
        tool_events = ToolEventRecorder()
        agent = create_mom_life_agent(session_id, tool_events, family_id=family_id)
        try:
            async for event in agent.stream_async(message):
                for completed in tool_events.drain():
                    yield _sse({"type": "tool_response", **completed})
                content = event.get("data")
                if isinstance(content, str) and content:
                    yield _sse({"type": "content", "content": content})
                tool_use = event.get("current_tool_use")
                if isinstance(tool_use, dict) and tool_use.get("toolUseId"):
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
