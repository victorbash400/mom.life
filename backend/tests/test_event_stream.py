import asyncio

from app.event_stream import FamilyEvents


def test_worker_thread_wakes_waiting_event_subscriber():
    async def run():
        events = FamilyEvents()
        queue = events.subscribe("family")
        waiting = asyncio.create_task(queue.get())
        await asyncio.sleep(0)
        await asyncio.to_thread(events.publish, "family", {"type": "simulator_changed"})
        assert await asyncio.wait_for(waiting, 0.1) == {"type": "simulator_changed"}
        events.unsubscribe("family", queue)
    asyncio.run(run())
