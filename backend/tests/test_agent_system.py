import asyncio
import json

from agents.goal_planner import AssignmentPlan, GoalPlan
from app.education_agent import EducationAgentManager
from app.event_stream import family_events
from app.goal_tasks import GoalTaskManager
from app.intake_agent import IntakeAgentManager
from app.security_agent import SecurityAgentManager
from app.task_store import TaskStore


class Families:
    @staticmethod
    def list_children(family_id):
        return [{"id": "amina", "family_id": family_id, "name": "Amina"}]

    @staticmethod
    def profile(family_id):
        return {"id": "parent", "family_id": family_id, "name": "Sarah"}

    @staticmethod
    def child(family_id, child_id):
        if child_id == "amina":
            return {"id": child_id, "family_id": family_id, "name": "Amina"}
        return None


def test_incoming_information_reaches_safety_education_and_completed_work(tmp_path, monkeypatch):
    from app import auth, education_agent, goal_tasks, intake_agent, security_agent

    store = TaskStore(tmp_path / "system.db")
    store.install_plugin("family", "google-workspace")
    monkeypatch.setattr(auth, "families", Families())

    async def route(_store, family_id, incoming_id):
        goal = store.create(family_id, "amina", "Prepare Amina's school-trip permission form")
        store.set_incoming(
            incoming_id,
            status="completed",
            action="create_goal",
            reason="The school requested a new permission form.",
            child_id="amina",
            goal_id=goal["id"],
        )
        store.add_intake_activity(incoming_id, "decision", "Created one new family outcome.", {"action": "create_goal"})
        return {"action": "create_goal", "goal_id": goal["id"], "child_id": "amina"}

    async def review_safety(_store, family_id, review_id):
        store.set_security_review(
            review_id,
            status="completed",
            action="alert",
            severity="moderate",
            category="Pickup change",
            summary="Confirm the unfamiliar pickup contact",
            reason="The notice names a new pickup contact that the family has not confirmed.",
        )
        store.add_security_activity(review_id, "decision", "Raised an evidence-grounded pickup alert.", {"action": "alert"})
        return {"action": "alert", "severity": "moderate"}

    async def review_education(_store, family_id, review_id):
        review = store.education_review(review_id, family_id)
        store.update_education_snapshot(
            family_id,
            "amina",
            "Amina's class is preparing for the museum trip and the school needs her permission form by Friday.",
            str(review["incoming_id"]),
        )
        store.set_education_review(review_id, status="completed", action="update", reason="The notice adds current class context.")
        return {"action": "update", "child_ids": ["amina"]}

    async def plan(_request, _child_id, skills, **_kwargs):
        skill = next(item for item in skills if item["slug"] == "school-notice-follow-through")
        return GoalPlan(operations=[AssignmentPlan(
            action="create",
            key="permission-form",
            title="Prepare permission form",
            instruction="Prepare the form from the school notice and preserve the deadline.",
            expected_outputs=["Prepared permission form"],
            skill_ids=[str(skill["id"])],
        )])

    async def work(prompt, _plugins, progress, expected_outputs, *_args):
        context = json.loads(prompt)
        assert "workspace.gmail" in context["permitted_namespaces"]
        assert "School Notice Follow-through" in context["selected_skill_instructions"]
        progress("Prepared the permission form from the school notice", 90, "Verify the deadline")
        return {
            "status": "completed",
            "summary": "Amina's permission form is prepared with Friday's deadline.",
            "evidence": "The completed assignment retained the school notice and deadline.",
            "outputs": [{"name": expected_outputs[0], "evidence": "Prepared from school notice school-1."}],
        }

    monkeypatch.setattr(intake_agent, "run_intake_agent", route)
    monkeypatch.setattr(security_agent, "run_security_agent", review_safety)
    monkeypatch.setattr(education_agent, "run_education_agent", review_education)
    monkeypatch.setattr(goal_tasks, "plan_goal", plan)
    monkeypatch.setattr(goal_tasks, "run_worker", work)

    async def run():
        goals = GoalTaskManager(store)
        safety = SecurityAgentManager(store)
        education = EducationAgentManager(store)
        intake = IntakeAgentManager(store, goals, safety, education)
        events = family_events.subscribe("family")
        item, created = await intake.receive(
            "family",
            "email",
            "school-1",
            sender="teacher@school.example",
            subject="Museum trip",
            content="Amina's permission form is due Friday. An unfamiliar volunteer is listed for pickup.",
        )
        assert created
        await asyncio.gather(*list(intake._tasks.values()), *list(safety._tasks.values()), *list(education._tasks.values()))
        await asyncio.gather(*list(goals._workers.values()))

        routed = store.incoming(str(item["id"]), "family")
        goal = store.get("family", str(routed["goal_id"]))
        safety_review = store.security_reviews("family")[0]
        snapshot = store.education_snapshot("family", "amina")
        assert routed["action"] == "create_goal"
        assert goal["status"] == "completed"
        assert goal["assignments"][0]["evidence"]["outputs"][0]["name"] == "Prepared permission form"
        assert safety_review["action"] == "alert"
        assert safety_review["summary"] == "Confirm the unfamiliar pickup contact"
        assert snapshot["source_ids"] == [str(item["id"])]

        event_types = []
        while not events.empty():
            event_types.append(events.get_nowait()["type"])
        assert {"intake_changed", "security_changed", "education_changed", "goals_changed"}.issubset(event_types)

        repeated, repeated_created = await intake.receive("family", "email", "school-1")
        assert not repeated_created
        assert repeated["id"] == item["id"]
        assert len(store.list("family")) == 1
        assert len(store.security_reviews("family")) == 1
        family_events.unsubscribe("family", events)

    asyncio.run(run())
