import asyncio
from io import BytesIO

from agents.agentcore_client import AgentCoreClient, runtime_session_id
from app.config import Settings


class RuntimeClient:
    def __init__(self, body: bytes):
        self.body = body
        self.request = None
        self.stream = None

    def invoke_agent_runtime(self, **request):
        self.request = request
        self.stream = BytesIO(self.body)
        return {"contentType": "text/event-stream", "response": self.stream}


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
    assert transport.stream.closed


def test_runtime_progress_is_delivered_before_result():
    transport = RuntimeClient(b'data: {"type":"progress","assignment_id":"step"}\n\n'
                              b'data: {"type":"result","result":{"status":"completed"}}\n\n')
    client = AgentCoreClient(Settings(_env_file=None, agentcore_runtime_arn="test"), transport)
    events = []
    result = asyncio.run(client.result("work", {}, session_id=runtime_session_id("work"), on_event=events.append))
    assert events[0] == {"type": "progress", "assignment_id": "step"}
    assert result == {"status": "completed"}


def test_runtime_stream_closes_when_a_read_fails():
    class BrokenStream(BytesIO):
        def readline(self):
            raise TimeoutError("Interrupted provider stream")

    transport = RuntimeClient(b"")
    stream = BrokenStream()
    transport.invoke_agent_runtime = lambda **kwargs: {"response": stream}
    client = AgentCoreClient(Settings(_env_file=None, agentcore_runtime_arn="test"), transport)
    import pytest
    with pytest.raises(TimeoutError, match="Interrupted provider stream"):
        asyncio.run(client.result("work", {}, session_id=runtime_session_id("work")))
    assert stream.closed


def test_runtime_session_ids_are_stable_and_valid():
    first = runtime_session_id("chat", "family", "chat")
    assert first == runtime_session_id("chat", "family", "chat")
    assert len(first) >= 33
