import asyncio
from io import BytesIO

from agents.agentcore_client import AgentCoreClient, runtime_session_id
from app.config import Settings


class RuntimeClient:
    def __init__(self, body: bytes):
        self.body = body
        self.request = None

    def invoke_agent_runtime(self, **request):
        self.request = request
        return {"contentType": "text/event-stream", "response": BytesIO(self.body)}


def test_runtime_client_streams_typed_events():
    transport = RuntimeClient(
        b'data: {"type":"content","content":"Checking."}\n\n'
        b'data: {"type":"result","result":{"status":"completed"}}\n\n'
    )
    settings = Settings(_env_file=None, agentcore_runtime_arn="arn:aws:bedrock-agentcore:us-east-1:123:runtime/test")
    client = AgentCoreClient(settings, transport)

    result = asyncio.run(client.result("work", {"goal_id": "goal"}, session_id=runtime_session_id("work", "goal")))

    assert result == {"status": "completed"}
    assert transport.request["qualifier"] == "DEFAULT"
    assert transport.request["accept"] == "text/event-stream"
    assert b'"operation": "work"' in transport.request["payload"]


def test_runtime_session_ids_are_stable_and_valid():
    first = runtime_session_id("chat", "family", "chat")
    assert first == runtime_session_id("chat", "family", "chat")
    assert len(first) >= 33
