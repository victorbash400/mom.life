import asyncio
import json
import logging

from agents.intake_agent import run_intake_agent
from app.event_stream import family_events
from app.runtime_lock import acquire_wait, release
from app.task_store import TaskStore, now


logger = logging.getLogger(__name__)


class IntakeAgentManager:
    def __init__(self, store: TaskStore, goal_tasks, security_agent=None, education_agent=None) -> None:
        self.store = store
        self.goal_tasks = goal_tasks
        self.security_agent = security_agent
        self.education_agent = education_agent
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._family_locks: dict[str, asyncio.Lock] = {}
        self._capacity = asyncio.Semaphore(4)

    async def recover(self) -> None:
        with self.store._connect() as connection:
            rows = connection.execute("SELECT id,family_id FROM incoming_items WHERE status IN ('queued','processing')").fetchall()
        for row in rows:
            await self.route_received(str(row["family_id"]), str(row["id"]))

    async def receive(
        self,
        family_id: str,
        source: str,
        provider_event_id: str,
        **content: object,
    ) -> tuple[dict[str, object], bool]:
        item, created = await asyncio.to_thread(self.store.receive_incoming, family_id, source, provider_event_id, **content)
        if created:
            await self.route_received(family_id, str(item["id"]))
        return item, created

    async def route_received(self, family_id: str, incoming_id: str) -> None:
        if self.security_agent:
            review, _ = await self.security_agent.receive(family_id, incoming_id)
            await self.security_agent.wait(str(review["id"]))
            review = await asyncio.to_thread(self.store.security_review, str(review["id"]), family_id)
            if not review or review["status"] != "completed" or (review["action"] == "alert" and not review["dismissed"]):
                await self._hold_for_safety(family_id, incoming_id)
                return
        await self.start(family_id, incoming_id, known_runnable=True)
        if self.education_agent:
            await self.education_agent.receive(family_id, incoming_id)

    async def _hold_for_safety(self, family_id: str, incoming_id: str) -> None:
        reason = "Held for Safety review before updating tasks or education."
        await asyncio.to_thread(
            self.store.set_incoming, incoming_id, status="completed", action="request_attention",
            reason=reason, attention_required=1, processed_at=now(),
        )
        await asyncio.to_thread(self.store.add_intake_activity, incoming_id, "safety_hold", reason)
        education, _ = await asyncio.to_thread(self.store.receive_education_review, family_id, incoming_id)
        await asyncio.to_thread(
            self.store.set_education_review, str(education["id"]), status="completed", action="ignore",
            reason=reason, failure="", processed_at=now(),
        )
        self._publish(family_id, incoming_id)
        family_events.publish(family_id, {"type": "education_changed"})

    async def start(self, family_id: str, incoming_id: str, *, known_runnable: bool = False) -> bool:
        current = self._tasks.get(incoming_id)
        if current and not current.done():
            return False
        if not known_runnable:
            item = await asyncio.to_thread(self.store.incoming, incoming_id, family_id)
            if not item or item["status"] not in {"queued", "processing", "failed"}:
                return False
        task = asyncio.create_task(self._run_locked(family_id, incoming_id), name=f"mom-life-intake-{incoming_id}")
        self._tasks[incoming_id] = task

        def finished(done) -> None:
            if self._tasks.get(incoming_id) is done:
                self._tasks.pop(incoming_id, None)

        task.add_done_callback(finished)
        return True

    async def _run_locked(self, family_id: str, incoming_id: str) -> None:
        async with self._capacity:
            async with self._family_locks.setdefault(family_id, asyncio.Lock()):
                lease = await asyncio.to_thread(acquire_wait, self.store.path, f"intake-family-{family_id}")
                try:
                    item = await asyncio.to_thread(self.store.incoming, incoming_id, family_id)
                    if not item or item["status"] not in {"queued", "processing", "failed"}:
                        return
                    if item["status"] == "processing":
                        await asyncio.to_thread(self.store.set_incoming, incoming_id, status="queued")
                    await self._run(family_id, incoming_id)
                finally:
                    await asyncio.to_thread(release, lease)

    async def retry(self, family_id: str, incoming_id: str, guidance: str = "") -> dict[str, object]:
        item = await asyncio.to_thread(self.store.incoming, incoming_id, family_id)
        if not item:
            raise ValueError("Incoming item not found.")
        if item["status"] == "processing":
            return item
        await asyncio.to_thread(self.store.set_incoming, incoming_id, status="queued", action="", reason="",
            attention_required=0, failure="", processed_at=None)
        await asyncio.to_thread(self.store.add_intake_activity, incoming_id, "retry",
            guidance.strip() or "Retry requested.", {"guidance": guidance.strip()})
        await asyncio.to_thread(self.store.reset_education_review, family_id, incoming_id)
        await self.route_received(family_id, incoming_id)
        return await asyncio.to_thread(self.store.incoming, incoming_id, family_id) or item

    async def shutdown(self) -> None:
        tasks = list(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self, incoming_id: str) -> None:
        task = self._tasks.pop(incoming_id, None)
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def _run(self, family_id: str, incoming_id: str) -> None:
        await asyncio.to_thread(self.store.set_incoming, incoming_id, status="processing", failure="")
        await asyncio.to_thread(self.store.add_intake_activity, incoming_id, "started", "Intake Agent started reading the item.")
        self._publish(family_id, incoming_id)
        try:
            decision = await run_intake_agent(self.store, family_id, incoming_id)
            goal_id = str(decision.get("goal_id") or "")
            if decision["action"] == "create_goal":
                await self.goal_tasks.start(family_id, goal_id)
            elif decision["action"] == "resume_goal":
                item = await asyncio.to_thread(self.store.incoming, incoming_id, family_id)
                if not item:
                    raise RuntimeError("The routed incoming item is unavailable.")
                instruction = (
                    "Revise this existing family outcome using newly received information. "
                    "Preserve completed evidence and do not duplicate the outcome.\n"
                    f"Source: {item['source']}\nSender: {item['sender']}\nSubject: {item['subject']}\n"
                    f"Information:\n{item['content']}\nProvider payload:\n{json.dumps(item['payload'], default=str)}"
                )
                await self.goal_tasks.revise(family_id, goal_id, instruction)
            self._publish(family_id, incoming_id)
        except asyncio.CancelledError:
            await asyncio.to_thread(self.store.set_incoming, incoming_id, status="queued")
            raise
        except Exception as error:
            message = str(error).strip() or type(error).__name__
            await asyncio.to_thread(self.store.set_incoming, incoming_id, status="failed", failure=message, attention_required=1)
            await asyncio.to_thread(self.store.add_intake_activity, incoming_id, "failed", message)
            self._publish(family_id, incoming_id)
            logger.exception("intake_agent incoming=%s status=failed", incoming_id)

    @staticmethod
    def _publish(family_id: str, incoming_id: str) -> None:
        family_events.publish(family_id, {"type": "intake_changed", "incoming_id": incoming_id})
