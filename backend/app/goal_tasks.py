import asyncio
import json
from datetime import UTC, datetime

from agents.goal_planner import plan_goal
from agents.goal_worker import run_worker
from app.event_stream import family_events
from app.skills import BUILTIN_SKILLS
from app.task_store import TaskStore
from plugins.runtime import PluginToolSession
from plugins.namespaces import namespaces
from app.plugin_service import PluginService
from app.runtime_lock import acquire, release

_ACTIVE_GOALS: set[str] = set()


class GoalTaskManager:
    def __init__(self, store: TaskStore) -> None:
        self.store = store
        self._workers: dict[str, asyncio.Task[bool]] = {}
        self._revisions: dict[str, asyncio.Lock] = {}
        self._capacity = asyncio.Semaphore(4)
        self._automation_manager = None

    async def start(self, family_id: str, goal_id: str, *, known_active: bool = False, automation_check: bool = False) -> bool:
        if self._automation_manager is not None and not automation_check:
            link = await asyncio.to_thread(self.store.automation_parent, goal_id)
            if link:
                await asyncio.to_thread(self._automation_manager.store.require_active_run, goal_id)
                if not (await asyncio.to_thread(self.store.get, family_id,goal_id)):
                    raise ValueError('Goal not found.')
                self._automation_manager.kick(family_id,link['goal_id'])
                return True
        existing = self._workers.get(goal_id)
        if (existing and not existing.done()) or goal_id in _ACTIVE_GOALS:
            return False
        if not known_active:
            goal = await asyncio.to_thread(self.store.get, family_id, goal_id)
            if not goal:
                raise ValueError("Goal not found.")
            if goal["status"] != "active":
                return False
        _ACTIVE_GOALS.add(goal_id)
        worker = asyncio.create_task(self._run_locked(family_id, goal_id), name=f"mom-life-goal-{goal_id}")
        self._workers[goal_id] = worker
        worker.add_done_callback(lambda done: _ACTIVE_GOALS.discard(goal_id))
        worker.add_done_callback(lambda done: self._workers.pop(goal_id, None) if self._workers.get(goal_id) is done else None)
        return True

    async def _run_locked(self, family_id: str, goal_id: str) -> bool:
        async with self._capacity:
            lease = await asyncio.to_thread(acquire, self.store.path, goal_id)
            if lease is None:
                return False
            try:
                goal = await asyncio.to_thread(self.store.get, family_id, goal_id)
                if not goal or goal["status"] != "active":
                    return False
                await self._orchestrate(family_id, goal_id)
                return True
            finally:
                release(lease)
                await asyncio.to_thread(self.store.notify_runtime_completion, goal_id)

    async def stop(self, goal_id: str) -> None:
        worker = self._workers.get(goal_id)
        if worker and not worker.done():
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)

    async def wait(self, goal_id: str) -> None:
        worker = self._workers.get(goal_id)
        if worker and worker is not asyncio.current_task():
            await asyncio.shield(worker)

    async def revise(self, family_id: str, goal_id: str, instruction: str) -> None:
        async with self._revisions.setdefault(goal_id, asyncio.Lock()):
            goal = await asyncio.to_thread(self.store.get, family_id, goal_id)
            if not goal:
                raise ValueError("Goal not found.")
            await self.stop(goal_id)
            async with self._capacity:
                lease = await asyncio.to_thread(acquire, self.store.path,goal_id)
                if lease is None:
                    raise ValueError("This goal is running in another backend process.")
                try:
                    from app.browser_cleanup import discard_goal_browser_sessions
                    await discard_goal_browser_sessions(self.store,goal_id)
                    await asyncio.to_thread(self.store.set_goal_state, goal_id, status="active")
                    await self._plan(family_id, (await asyncio.to_thread(self.store.get, family_id, goal_id)), instruction)
                except Exception as error:
                    await asyncio.to_thread(self.store.set_goal_state, goal_id, run_state="failed", current_step=str(error))
                    self._publish(family_id, goal_id)
                    raise
                finally:
                    release(lease)
            await self.start(family_id, goal_id)

    async def shutdown(self):
        for goal_id in list(self._workers):
            await self.stop(goal_id)

    async def _orchestrate(self, family_id: str, goal_id: str) -> None:
        try:
            goal = await asyncio.to_thread(self.store.get, family_id, goal_id)
            if not goal:
                return
            if not (await asyncio.to_thread(self.store.assignments, goal_id)):
                await self._plan(family_id, goal)
            while True:
                goal = await asyncio.to_thread(self.store.get, family_id, goal_id)
                if not goal or goal["status"] != "active":
                    return
                assignments = await asyncio.to_thread(self.store.assignments, goal_id)
                pending = [a for a in assignments if a["status"] not in {"completed", "cancelled"}]
                if not pending:
                    completed = [a for a in assignments if a["status"] == "completed"]
                    if not completed:
                        await asyncio.to_thread(self.store.set_goal_state, goal_id,status="paused",run_state="paused",current_step="No remaining assignments")
                    else:
                        summary = "\n".join(str(a["report"]) for a in completed)
                        await asyncio.to_thread(self.store.set_goal_state, goal_id,status="completed",run_state="completed",progress=100,current_step=summary,report=summary)
                        await asyncio.to_thread(self.store.add_activity, goal_id,"goal_completed",summary)
                    self._publish(family_id,goal_id)
                    return
                completed_ids = {a["id"] for a in assignments if a["status"] == "completed"}
                ready = next((a for a in pending if a["status"] == "queued" and set(a["depends_on"]).issubset(completed_ids)),None)
                if not ready:
                    await asyncio.to_thread(self.store.set_goal_state, goal_id,run_state="blocked",current_step="Waiting for an answer, retry, or dependency")
                    self._publish(family_id,goal_id)
                    return
                if await self._run_assignment(family_id,goal,ready) not in {"completed", "queued"}:
                    return
        except asyncio.CancelledError:
            for assignment in (await asyncio.to_thread(self.store.assignments, goal_id)):
                if assignment["status"] == "running":
                    await asyncio.to_thread(self.store.set_assignment, str(assignment["id"]),status="queued",phase="queued")
            await asyncio.to_thread(self.store.set_goal_state, goal_id,status="paused",run_state="paused",current_step="Paused")
            self._publish(family_id,goal_id)
            raise
        except Exception as error:
            message = str(error).strip() or type(error).__name__
            await asyncio.to_thread(self.store.set_goal_state, goal_id,run_state="failed",current_step=message,report=message)
            await asyncio.to_thread(self.store.add_activity, goal_id,"run_failed",message)
            self._publish(family_id,goal_id)

    async def _plan(self, family_id: str, goal: dict[str, object], instruction: str | None = None) -> list[dict[str, object]]:
        await asyncio.to_thread(self.store.seed_skills, family_id, BUILTIN_SKILLS)
        states = {p["id"]:p for p in await asyncio.to_thread(PluginService(self.store).list, family_id)}
        skills = await asyncio.to_thread(self.store.skills, family_id)
        for skill in skills:
            required = list(skill["required_plugin_ids"])
            skill["available"] = all(plugin_id in states for plugin_id in required)
            skill["connection_setup_required"] = [plugin_id for plugin_id in required if not states.get(plugin_id, {}).get("connected")]
        await asyncio.to_thread(self.store.set_goal_state, str(goal["id"]), run_state="planning", current_step="Defining the work")
        self._publish(family_id, str(goal["id"]))
        request = str(goal["text"])
        if instruction:
            request = f"Original family outcome:\n{request}\n\nRevision information:\n{instruction}"
        valid = {str(skill["id"]):skill for skill in skills}
        ledger = await asyncio.to_thread(self.store.assignments, str(goal["id"]))
        plan_request = request
        for attempt in range(2):
            plan = await plan_goal(plan_request, str(goal["child_id"]), skills, existing_tasks=ledger,
                                   plugins=[{'id':p['id'],'name':p['name'],'connected':p['connected']} for p in states.values()])
            try:
                for operation in plan.operations:
                    operation.skill_ids = _resolve_skill_ids(operation.skill_ids, skills)
                    if any(identity not in valid or not valid[identity]["available"] for identity in operation.skill_ids):
                        raise ValueError("The planner selected an unknown or unavailable skill.")
                    if any(identity not in states for identity in operation.plugin_ids):
                        raise ValueError("The planner selected an unknown plugin.")
                await asyncio.to_thread(self.store.apply_plan, family_id,str(goal["id"]),plan.operations)
                break
            except ValueError as error:
                if attempt:
                    raise
                plan_request = f"{request}\n\nCorrect the plan using the existing task ledger. The prior plan was invalid: {error}"
        assignments = await asyncio.to_thread(self.store.assignments, str(goal["id"]))
        selected = list(dict.fromkeys(identity for item in assignments if item["status"] != "cancelled" for identity in item["skill_ids"]))
        plugins = list(dict.fromkeys(identity for item in assignments if item['status'] != 'cancelled' for identity in (item['plugin_ids'] or [p for s in item['skill_ids'] for p in valid[s]['required_plugin_ids']])))
        await asyncio.to_thread(self.store.set_goal_state, str(goal["id"]),run_state="queued",current_step="Ready to begin",skill_ids=selected,plugin_ids=plugins)
        await asyncio.to_thread(self.store.add_activity, str(goal["id"]),"plan_revised" if instruction else "plan_created",instruction or "Created the assignment board",plan.model_dump())
        self._publish(family_id,str(goal["id"]))
        return assignments

    async def _run_assignment(self, family_id: str, goal: dict[str, object], assignment: dict[str, object]) -> str:
        skills = {str(skill["id"]): skill for skill in (await asyncio.to_thread(self.store.skills, family_id))}
        if any(skill_id not in skills for skill_id in assignment["skill_ids"]):
            raise ValueError("An assigned skill no longer exists.")
        selected = [skills[skill_id] for skill_id in assignment["skill_ids"]]
        plugin_ids = list(dict.fromkeys(assignment['plugin_ids'] or [plugin_id for skill in selected for plugin_id in skill["required_plugin_ids"]]))
        instructions = "\n\n".join(f"Skill: {skill['name']}\n{skill['instructions']}" for skill in selected)
        dependencies = [item for item in (await asyncio.to_thread(self.store.assignments, str(goal["id"]))) if item["id"] in assignment["depends_on"]]
        handoff = [{"title": item["title"], "summary": item["report"], "evidence": item["evidence"]} for item in dependencies]
        prompt = json.dumps({
            "goal_id": goal["id"], "child_id": goal["child_id"], "assignment_id": assignment["id"],
            "instruction": assignment["instruction"], "required_inputs": assignment["required_inputs"],
            "expected_outputs": assignment["expected_outputs"], "dependency_evidence": handoff,
            "selected_skill_instructions": instructions,
            "permitted_namespaces": namespaces(plugin_ids),
            "mom_answers": (await asyncio.to_thread(self.store.questions, str(goal["id"]))),
            "previous_run_evidence": (await asyncio.to_thread(self.store.get, family_id,str(goal["id"])))["activities"],
            "calendar_preferences": (await asyncio.to_thread(self.store.calendar_preferences, family_id)),
        })
        await asyncio.to_thread(self.store.set_assignment, str(assignment["id"]), status="running", phase="working", started_at=datetime.now(UTC).isoformat())
        await asyncio.to_thread(self.store.set_goal_state, str(goal["id"]), run_state="running", current_step=str(assignment["title"]))
        self._publish(family_id, str(goal["id"]))

        def progress(message: str, percent: int, next_step: str) -> None:
            self.store.set_assignment(str(assignment["id"]), current_step=message, progress=percent, next_step=next_step)
            self.store.set_goal_state(str(goal["id"]), current_step=message, progress=percent)
            self.store.add_activity(str(goal["id"]), "worker_update", message, {"assignment_id": assignment["id"], "next_step": next_step})
            self._publish(family_id, str(goal["id"]))

        plugins = PluginToolSession(plugin_ids,self.store,family_id,str(goal["child_id"]))
        plugins.assignment_id = str(assignment["id"])
        try:
            result = await run_worker(prompt,plugins,progress,list(assignment["expected_outputs"]),self.store,str(goal["id"]),str(assignment["id"]))
            plugins.preserve_browser = result.get("status") == "blocked" and not result.get("external_wait")
        except Exception as error:
            message = str(error).strip() or type(error).__name__
            await asyncio.to_thread(self.store.set_assignment, str(assignment["id"]), status="failed", phase="failed", finished_at=datetime.now(UTC).isoformat(), report=message, current_step=message)
            raise
        finally:
            await plugins.close()
        if result["status"] == "blocked" and result.get("external_wait"):
            status = await asyncio.to_thread(self.store.finish_provider_wait, goal["id"], assignment["id"], result["question"])
            self._publish(family_id,str(goal["id"]))
            return status
        if result["status"] == "blocked":
            question = str(result["question"])
            await asyncio.to_thread(self.store.set_assignment, str(assignment["id"]), status="blocked", phase="blocked", finished_at=datetime.now(UTC).isoformat(), report=question, current_step=question)
            await asyncio.to_thread(self.store.set_goal_state, str(goal["id"]), run_state="blocked", current_step=question)
            await asyncio.to_thread(self.store.add_activity, str(goal["id"]), "needs_mom", question, {"context": result.get("context", "")})
            self._publish(family_id, str(goal["id"]))
            return "blocked"
        expected = list(assignment["expected_outputs"])
        observed = {item.get("name", "").strip().casefold(): item.get("evidence", "").strip() for item in result.get("outputs", [])}
        if result.get("status") != "completed" or not result.get("summary") or not result.get("evidence") or any(not observed.get(name.strip().casefold()) for name in expected):
            await asyncio.to_thread(self.store.set_assignment, str(assignment["id"]),status="failed",phase="failed",report="Completion evidence is incomplete")
            raise ValueError("Completion evidence is incomplete")
        summary = str(result["summary"])
        evidence = {"evidence": result["evidence"], "outputs": result["outputs"]}
        await asyncio.to_thread(self.store.set_assignment, str(assignment["id"]), status="completed", phase="completed", progress=100,
                                current_step=summary, report=summary, evidence=evidence, finished_at=datetime.now(UTC).isoformat())
        await asyncio.to_thread(self.store.add_activity, str(goal["id"]), "task_completed", summary, evidence)
        self._publish(family_id, str(goal["id"]))
        return "completed"

    @staticmethod
    def _publish(family_id: str, goal_id: str) -> None:
        family_events.publish(family_id, {"type": "goals_changed", "goal_id": goal_id})


def _resolve_skill_ids(references: list[str], skills: list[dict[str, object]]) -> list[str]:
    aliases: dict[str, str | None] = {}
    for skill in skills:
        identity = str(skill["id"])
        for value in (identity, skill.get("slug"), skill.get("name")):
            if not value:
                continue
            alias = str(value).strip().casefold()
            if alias not in aliases:
                aliases[alias] = identity
            elif aliases[alias] != identity:
                aliases[alias] = None

    resolved: list[str] = []
    for reference in references:
        identity = aliases.get(str(reference).strip().casefold())
        if not identity:
            raise ValueError("The planner selected a skill that is not in this family's library.")
        if identity not in resolved:
            resolved.append(identity)
    return resolved
