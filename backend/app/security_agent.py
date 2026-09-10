import asyncio
import logging

from agents.security_agent import run_security_agent
from app.event_stream import family_events
from app.runtime_lock import acquire, release
from app.task_store import TaskStore, now


logger = logging.getLogger(__name__)


class SecurityAgentManager:
    def __init__(self, store: TaskStore) -> None:
        self.store = store
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def recover(self) -> None:
        with self.store._connect() as connection:
            rows = connection.execute("SELECT id,family_id FROM security_reviews WHERE status IN ('queued','processing')").fetchall()
            connection.execute("UPDATE security_reviews SET status='queued' WHERE status='processing'")
        for row in rows:
            await self.start(str(row["family_id"]), str(row["id"]))

    async def receive(self, family_id: str, incoming_id: str) -> tuple[dict[str, object], bool]:
        review, created = self.store.receive_security_review(family_id, incoming_id)
        if created:
            await self.start(family_id, str(review["id"]))
        return review, created

    async def start(self, family_id: str, review_id: str) -> bool:
        current = self._tasks.get(review_id)
        if current and not current.done():
            return False
        review = self.store.security_review(review_id, family_id)
        if not review or review["status"] not in {"queued", "failed"}:
            return False
        lease = acquire(self.store.path, f"security-{review_id}")
        if lease is None:
            return False
        task = asyncio.create_task(self._run(family_id, review_id), name=f"mom-life-security-{review_id}")
        self._tasks[review_id] = task

        def finished(done) -> None:
            release(lease)
            if self._tasks.get(review_id) is done:
                self._tasks.pop(review_id, None)

        task.add_done_callback(finished)
        return True

    async def retry(self, family_id: str, review_id: str) -> dict[str, object]:
        review = self.store.security_review(review_id, family_id)
        if not review:
            raise ValueError("Safety review not found.")
        if review["status"] == "processing":
            return review
        self.store.set_security_review(
            review_id,
            status="queued",
            action="",
            severity="",
            category="",
            summary="",
            reason="",
            failure="",
            processed_at=None,
        )
        self.store.add_security_activity(review_id, "retry", "Retry requested.")
        await self.start(family_id, review_id)
        return self.store.security_review(review_id, family_id) or review

    async def shutdown(self) -> None:
        tasks = list(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run(self, family_id: str, review_id: str) -> None:
        settings = self.store.security_settings(family_id)
        if not settings["enabled"]:
            self.store.set_security_review(
                review_id,
                status="completed",
                action="ignore",
                reason="Safety monitoring is turned off.",
                processed_at=now(),
            )
            self.store.add_security_activity(review_id, "decision", "Safety monitoring is turned off.", {"action": "ignore"})
            self._publish(family_id, review_id)
            return
        self.store.set_security_review(review_id, status="processing", failure="")
        self.store.add_security_activity(review_id, "started", "Safety Agent started reviewing the item.")
        self._publish(family_id, review_id)
        try:
            await asyncio.to_thread(asyncio.run, run_security_agent(self.store, family_id, review_id))
            self._publish(family_id, review_id)
        except asyncio.CancelledError:
            self.store.set_security_review(review_id, status="queued")
            raise
        except Exception as error:
            message = str(error).strip() or type(error).__name__
            self.store.set_security_review(review_id, status="failed", failure=message)
            self.store.add_security_activity(review_id, "failed", message)
            self._publish(family_id, review_id)
            logger.exception("security_agent review=%s status=failed", review_id)

    @staticmethod
    def _publish(family_id: str, review_id: str) -> None:
        family_events.publish(family_id, {"type": "security_changed", "review_id": review_id})
