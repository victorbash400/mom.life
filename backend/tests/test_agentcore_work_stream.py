import asyncio

import agentcore_main


def test_hosted_worker_streams_progress_before_completion(monkeypatch):
    async def verify():
        finish = asyncio.Event()

        async def work(payload, on_progress):
            on_progress({"type": "progress", "assignment_id": "step"})
            await finish.wait()
            return {"status": "completed"}

        monkeypatch.setattr(agentcore_main, "_work", work)
        stream = agentcore_main.invoke({"operation": "work"})
        assert await anext(stream) == {"type": "progress", "assignment_id": "step"}
        finish.set()
        assert await anext(stream) == {"type": "result", "result": {"status": "completed"}}
        await stream.aclose()

    asyncio.run(verify())


def test_disconnected_worker_stream_cancels_and_cleans_up(monkeypatch):
    async def verify():
        cleaned = asyncio.Event()

        async def work(payload, on_progress):
            try:
                on_progress({"type": "progress"})
                await asyncio.Event().wait()
            finally:
                cleaned.set()

        monkeypatch.setattr(agentcore_main, "_work", work)
        stream = agentcore_main.invoke({"operation": "work"})
        await anext(stream)
        await stream.aclose()
        assert cleaned.is_set()

    asyncio.run(verify())
