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
        self._capacity = asyncio.Semaphore(4)

    async def recover(self) -> None:
        with self.store._connect() as connection:
            rows = connection.execute("SELECT id,family_id FROM security_reviews WHERE status IN ('queued','processing')").fetchall()
        for row in rows:
            await self.start(str(row["family_id"]), str(row["id"]))

    async def receive(self, family_id: str, incoming_id: str, *, manual: bool = False) -> tuple[dict[str, object], bool]:
        if not await asyncio.to_thread(self.store.incoming,incoming_id,family_id):
            raise ValueError('Safety evidence not found in this family.')
        review, created = await asyncio.to_thread(self.store.receive_security_review, family_id, incoming_id)
        settings = await asyncio.to_thread(self.store.security_settings,family_id)
        item = review['incoming']
        allowed = settings['enabled'] and item and self.store.security_scope_matches(settings,item) and (manual or settings['review_mode'] == 'incoming')
        if manual and allowed and not created and review['status'] == 'completed' and review['action'] == 'ignore':
            await asyncio.to_thread(self.store.set_security_review,review['id'],status='queued',action='',reason='',processed_at=None)
            created = True
        runnable = created or review['status'] == 'queued'
        if runnable and not allowed:
            await asyncio.to_thread(self.store.set_security_review,review['id'],status='completed',action='ignore',reason='Outside the configured automatic review scope.',processed_at=now())
        if runnable and allowed:
            await self.start(family_id, str(review["id"]), known_runnable=True)
        return review, created

    async def start(self, family_id: str, review_id: str, *, known_runnable: bool = False) -> bool:
        current = self._tasks.get(review_id)
        if current and not current.done():
            return False
        if not known_runnable:
            review = await asyncio.to_thread(self.store.security_review, review_id, family_id)
            if not review or review["status"] not in {"queued", "processing", "failed"}:
                return False
        task = asyncio.create_task(self._run_locked(family_id, review_id), name=f"mom-life-security-{review_id}")
        self._tasks[review_id] = task

        def finished(done) -> None:
            if self._tasks.get(review_id) is done:
                self._tasks.pop(review_id, None)

        task.add_done_callback(finished)
        return True

    async def _run_locked(self, family_id: str, review_id: str) -> None:
        async with self._capacity:
            lease = await asyncio.to_thread(acquire, self.store.path, f"security-{review_id}")
            if lease is None:
                return
            try:
                review = await asyncio.to_thread(self.store.security_review, review_id, family_id)
                if not review or review["status"] not in {"queued", "processing", "failed"}:
                    return
                if review["status"] == "processing":
                    await asyncio.to_thread(self.store.set_security_review, review_id, status="queued")
                await self._run(family_id, review_id)
            finally:
                await asyncio.to_thread(release, lease)

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

    async def stop(self, review_id: str) -> None:
        task = self._tasks.pop(review_id, None)
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def _run(self, family_id: str, review_id: str) -> None:
        settings = await asyncio.to_thread(self.store.security_settings, family_id)
        review = await asyncio.to_thread(self.store.security_review,review_id,family_id)
        if not settings["enabled"] or not review or not review['incoming'] or not self.store.security_scope_matches(settings,review['incoming']):
            reason = 'Safety monitoring is turned off.' if not settings['enabled'] else 'This item is outside the selected safety scope.'
            await asyncio.to_thread(
                self.store.set_security_review, review_id, status="completed", action="ignore",
                reason=reason, processed_at=now(),
            )
            await asyncio.to_thread(
                self.store.add_security_activity, review_id, "decision",
                reason, {"action": "ignore"},
            )
            self._publish(family_id, review_id)
            return
        await asyncio.to_thread(self.store.set_security_review, review_id, status="processing", failure="")
        await asyncio.to_thread(self.store.add_security_activity, review_id, "started", "Safety Agent started reviewing the item.")
        self._publish(family_id, review_id)
        try:
            await run_security_agent(self.store, family_id, review_id)
            self._publish(family_id, review_id)
        except asyncio.CancelledError:
            await asyncio.to_thread(self.store.set_security_review, review_id, status="queued")
            raise
        except Exception as error:
            message = str(error).strip() or type(error).__name__
            await asyncio.to_thread(self.store.set_security_review, review_id, status="failed", failure=message)
            await asyncio.to_thread(self.store.add_security_activity, review_id, "failed", message)
            self._publish(family_id, review_id)
            logger.exception("security_agent review=%s status=failed", review_id)

    @staticmethod
    def _publish(family_id: str, review_id: str) -> None:
        family_events.publish(family_id, {"type": "security_changed", "review_id": review_id})
