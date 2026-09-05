import asyncio
from collections import defaultdict


class FamilyEvents:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, object]]]] = defaultdict(set)

    def subscribe(self, family_id: str) -> asyncio.Queue[dict[str, object]]:
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=32)
        self._subscribers[family_id].add(queue)
        return queue

    def unsubscribe(self, family_id: str, queue: asyncio.Queue[dict[str, object]]) -> None:
        self._subscribers[family_id].discard(queue)

    def publish(self, family_id: str, event: dict[str, object]) -> None:
        for queue in tuple(self._subscribers[family_id]):
            if queue.full():
                queue.get_nowait()
                queue.put_nowait({"type":"goals_changed"})
            else:
                queue.put_nowait(event)


family_events = FamilyEvents()
