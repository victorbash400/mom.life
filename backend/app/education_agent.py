import asyncio
import logging

from agents.education_agent import run_education_agent
from app.event_stream import family_events
from app.runtime_lock import acquire, release
from app.task_store import TaskStore


logger = logging.getLogger(__name__)


class EducationAgentManager:
    def __init__(self, store: TaskStore) -> None:
        self.store = store
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._family_locks: dict[str, asyncio.Lock] = {}
        self._capacity = asyncio.Semaphore(4)

    async def recover(self) -> None:
        with self.store._connect() as connection:
            rows = connection.execute("SELECT id,family_id FROM education_reviews WHERE status IN ('queued','processing')").fetchall()
            unreviewed = connection.execute(
                """SELECT incoming_items.id,incoming_items.family_id FROM incoming_items
                LEFT JOIN education_reviews ON education_reviews.incoming_id=incoming_items.id
                AND education_reviews.family_id=incoming_items.family_id
                WHERE education_reviews.id IS NULL"""
            ).fetchall()
        for row in rows:
            await self.start(str(row["family_id"]), str(row["id"]))
        for row in unreviewed:
            await self.receive(str(row["family_id"]), str(row["id"]))

    async def receive(self, family_id: str, incoming_id: str) -> tuple[dict[str, object], bool]:
        review, created = await asyncio.to_thread(self.store.receive_education_review, family_id, incoming_id)
        if created or review["status"] in {"queued", "failed"}:
            await self.start(family_id, str(review["id"]), known_runnable=True)
        return review, created

    async def start(self, family_id: str, review_id: str, *, known_runnable: bool = False) -> bool:
        current = self._tasks.get(review_id)
        if current and not current.done():
            return False
        if not known_runnable:
            review = await asyncio.to_thread(self.store.education_review, review_id, family_id)
            if not review or review["status"] not in {"queued", "processing", "failed"}:
                return False
        task = asyncio.create_task(self._run_locked(family_id, review_id), name=f"mom-life-education-{review_id}")
        self._tasks[review_id] = task

        def finished(done) -> None:
            if self._tasks.get(review_id) is done:
                self._tasks.pop(review_id, None)

        task.add_done_callback(finished)
        return True

    async def _run_locked(self, family_id: str, review_id: str) -> None:
        async with self._capacity:
            lease = await asyncio.to_thread(acquire, self.store.path, f"education-{review_id}")
            if lease is None:
                return
            try:
                review = await asyncio.to_thread(self.store.education_review, review_id, family_id)
                if not review or review["status"] not in {"queued", "processing", "failed"}:
                    return
                if review["status"] == "processing":
                    await asyncio.to_thread(self.store.set_education_review, review_id, status="queued")
                await self._run(family_id, review_id)
            finally:
                await asyncio.to_thread(release, lease)

    async def shutdown(self) -> None:
        tasks = list(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self, review_id: str) -> None:
        task = self._tasks.pop(review_id, None)
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def _run(self, family_id: str, review_id: str) -> None:
        lock = self._family_locks.setdefault(family_id, asyncio.Lock())
        async with lock:
            await self._review(family_id, review_id)

    async def _review(self, family_id: str, review_id: str) -> None:
        review = await asyncio.to_thread(self.store.education_review, review_id, family_id)
        if not review or review["status"] == "completed":
            return
        item = await asyncio.to_thread(self.store.incoming, str(review["incoming_id"]), family_id)
        if item and any(activity["kind"] == "safety_hold" for activity in item["activities"]) and item["attention_required"]:
            return
        await asyncio.to_thread(self.store.set_education_review, review_id, status="processing", failure="")
        try:
            await run_education_agent(self.store, family_id, review_id)
            family_events.publish(family_id, {"type": "education_changed"})
        except asyncio.CancelledError:
            await asyncio.to_thread(self.store.set_education_review, review_id, status="queued")
            raise
        except Exception as error:
            message = str(error).strip() or type(error).__name__
            await asyncio.to_thread(self.store.set_education_review, review_id, status="failed", failure=message)
            logger.exception("education_agent review=%s status=failed", review_id)
