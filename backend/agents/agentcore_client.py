"""Typed invocation boundary for the hosted mom.life Strands runtime."""
import asyncio
import json
from collections.abc import AsyncIterator
from uuid import NAMESPACE_URL, uuid5

import boto3
from botocore.config import Config

from app.config import Settings, get_settings


def runtime_session_id(*parts: str) -> str:
    """Return a stable AgentCore session ID that satisfies its 33 character minimum."""
    return str(uuid5(NAMESPACE_URL, ":".join(parts)))


class AgentCoreClient:
    def __init__(self, settings: Settings | None = None, client=None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.agentcore_runtime_arn:
            raise ValueError("MOM_LIFE_AGENTCORE_RUNTIME_ARN is required for hosted agent execution.")
        self.client = client or boto3.Session(
            profile_name=self.settings.aws_profile or None,
            region_name=self.settings.strands_region,
        ).client("bedrock-agentcore", config=Config(read_timeout=120, retries={"total_max_attempts": 1}))

    async def events(self, operation: str, payload: dict, *, session_id: str) -> AsyncIterator[dict]:
        response = await asyncio.to_thread(
            self.client.invoke_agent_runtime,
            agentRuntimeArn=self.settings.agentcore_runtime_arn,
            qualifier=self.settings.agentcore_runtime_qualifier,
            runtimeSessionId=session_id,
            contentType="application/json",
            accept="text/event-stream",
            payload=json.dumps({"operation": operation, **payload}, default=str).encode(),
        )
        body = response["response"]
        try:
            while True:
                line = await asyncio.to_thread(body.readline)
                if not line:
                    break
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                line = line.strip()
                if line.startswith("data:"):
                    event = json.loads(line.removeprefix("data:").strip())
                    if isinstance(event, dict):
                        yield event
        finally:
            body.close()

    async def result(self, operation: str, payload: dict, *, session_id: str, on_event=None) -> dict:
        result = None
        async for event in self.events(operation, payload, session_id=session_id):
            if on_event is not None:
                on_event(event)
            if event.get("type") == "error":
                raise RuntimeError(str(event.get("error") or "AgentCore invocation failed."))
            if event.get("type") == "result":
                result = event.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("AgentCore returned no result.")
        return result
