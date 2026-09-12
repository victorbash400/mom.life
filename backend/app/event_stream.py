import asyncio
from collections import defaultdict


class FamilyEvents:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, object]]]] = defaultdict(set)
        self._loops = {}

    def subscribe(self, family_id: str) -> asyncio.Queue[dict[str, object]]:
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=32)
        self._subscribers[family_id].add(queue)
        try:
            self._loops[queue] = asyncio.get_running_loop()
        except RuntimeError:
            self._loops[queue] = None
        return queue

    def unsubscribe(self, family_id: str, queue: asyncio.Queue[dict[str, object]]) -> None:
        self._subscribers[family_id].discard(queue)
        self._loops.pop(queue, None)

    def publish(self, family_id: str, event: dict[str, object]) -> None:
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None
        for queue in tuple(self._subscribers[family_id]):
            loop = self._loops.get(queue)
            if loop is not None and loop is not current_loop:
                if not loop.is_closed():
                    loop.call_soon_threadsafe(self._deliver, queue, event)
            else:
                self._deliver(queue, event)

    @staticmethod
    def _deliver(queue, event):
        if queue.full():
            queue.get_nowait()
            queue.put_nowait({"type":"goals_changed"})
        else:
            queue.put_nowait(event)


family_events = FamilyEvents()
