import asyncio
import json
import logging

from agents.intake_agent import run_intake_agent
from app.event_stream import family_events
from app.runtime_lock import acquire, release
from app.task_store import TaskStore


logger = logging.getLogger(__name__)


class IntakeAgentManager:
    def __init__(self, store: TaskStore, goal_tasks, security_agent=None, education_agent=None) -> None:
        self.store = store
        self.goal_tasks = goal_tasks
        self.security_agent = security_agent
        self.education_agent = education_agent
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def recover(self) -> None:
        with self.store._connect() as connection:
            rows = connection.execute("SELECT id,family_id FROM incoming_items WHERE status IN ('queued','processing')").fetchall()
            connection.execute("UPDATE incoming_items SET status='queued' WHERE status='processing'")
        for row in rows:
            await self.start(str(row["family_id"]), str(row["id"]))

    async def receive(
        self,
        family_id: str,
        source: str,
        provider_event_id: str,
        **content: object,
    ) -> tuple[dict[str, object], bool]:
        item, created = self.store.receive_incoming(family_id, source, provider_event_id, **content)
        if created:
            await self.start(family_id, str(item["id"]))
            if self.security_agent:
                await self.security_agent.receive(family_id, str(item["id"]))
            if self.education_agent:
                await self.education_agent.receive(family_id, str(item["id"]))
        return item, created

    async def start(self, family_id: str, incoming_id: str) -> bool:
        current = self._tasks.get(incoming_id)
        if current and not current.done():
            return False
        item = self.store.incoming(incoming_id, family_id)
        if not item or item["status"] not in {"queued", "failed"}:
            return False
        lease = acquire(self.store.path, f"intake-{incoming_id}")
        if lease is None:
            return False
        task = asyncio.create_task(self._run(family_id, incoming_id), name=f"mom-life-intake-{incoming_id}")
        self._tasks[incoming_id] = task

        def finished(done) -> None:
            release(lease)
            if self._tasks.get(incoming_id) is done:
                self._tasks.pop(incoming_id, None)

        task.add_done_callback(finished)
        return True

    async def retry(self, family_id: str, incoming_id: str, guidance: str = "") -> dict[str, object]:
        item = self.store.incoming(incoming_id, family_id)
        if not item:
            raise ValueError("Incoming item not found.")
        if item["status"] == "processing":
            return item
        self.store.set_incoming(
            incoming_id,
            status="queued",
            action="",
            reason="",
            attention_required=0,
            failure="",
            processed_at=None,
        )
        self.store.add_intake_activity(incoming_id, "retry", guidance.strip() or "Retry requested.", {"guidance": guidance.strip()})
        await self.start(family_id, incoming_id)
        return self.store.incoming(incoming_id, family_id) or item

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
        self.store.set_incoming(incoming_id, status="processing", failure="")
        self.store.add_intake_activity(incoming_id, "started", "Intake Agent started reading the item.")
        self._publish(family_id, incoming_id)
        try:
            decision = await asyncio.to_thread(asyncio.run, run_intake_agent(self.store, family_id, incoming_id))
            goal_id = str(decision.get("goal_id") or "")
            if decision["action"] == "create_goal":
                await self.goal_tasks.start(family_id, goal_id)
            elif decision["action"] == "resume_goal":
                item = self.store.incoming(incoming_id, family_id)
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
            self.store.set_incoming(incoming_id, status="queued")
            raise
        except Exception as error:
            message = str(error).strip() or type(error).__name__
            self.store.set_incoming(incoming_id, status="failed", failure=message, attention_required=1)
            self.store.add_intake_activity(incoming_id, "failed", message)
            self._publish(family_id, incoming_id)
            logger.exception("intake_agent incoming=%s status=failed", incoming_id)

    @staticmethod
    def _publish(family_id: str, incoming_id: str) -> None:
        family_events.publish(family_id, {"type": "intake_changed", "incoming_id": incoming_id})
