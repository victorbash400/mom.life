import asyncio
from datetime import date
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field

from app.simulator import SimulatorService


router = APIRouter(prefix="/api/simulator")


class SimulatedMessage(BaseModel):
    profile_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=4000)
    sender: str | None = Field(default=None, min_length=1, max_length=128)


class SimulatedHealth(BaseModel):
    child_id: str = Field(min_length=1, max_length=128)
    date: date
    steps: int = Field(ge=0, le=100000)
    sleep_hours: float = Field(ge=0, le=24)
    heart_rate: int = Field(ge=20, le=240)
    active_energy: float = Field(ge=0, le=10000)
    distance: float = Field(ge=0, le=200000)


def service():
    from app.auth import families
    from app.main import task_store
    return SimulatorService(task_store, families)


@router.get("")
def simulator_state(request: Request):
    return service().state(request.state.family_id)


@router.put("/connections/{plugin_id}")
def connect(plugin_id: str, request: Request):
    try:
        return service().connect(request.state.family_id, plugin_id)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@router.delete("/connections/{plugin_id}", status_code=204)
def disconnect(plugin_id: str, request: Request):
    try:
        service().disconnect(request.state.family_id, plugin_id)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@router.post("/whatsapp/messages", status_code=201)
async def send_message(body: SimulatedMessage, request: Request, background_tasks: BackgroundTasks):
    from app.auth import families
    from app.main import automations, family_events, goal_tasks, intake_agent, task_store
    family_id = request.state.family_id
    profile = families.profile(family_id) if body.profile_id == "parent" else families.child(family_id, body.profile_id)
    if not profile:
        raise HTTPException(404, "Simulated family profile not found.")
    if body.sender is not None and not body.sender.strip():
        raise HTTPException(400, "Enter a message sender.")
    sender = body.sender.strip() if body.sender is not None else profile["name"]
    correlation = f"sim:{body.profile_id}" if body.sender is None else f"sim:{body.profile_id}:contact:{sender}"
    event_id = f"sim-wa-{uuid4()}"
    payload = {"id": event_id, "from": correlation, "sender": sender, "recipient_id": body.profile_id, "inbox_message": body.sender is not None, "text": {"body": body.text.strip()}, "simulated": True, "profile_id": body.profile_id,
               "child_id": body.profile_id if body.profile_id != "parent" else ""}
    try:
        routed = await asyncio.to_thread(task_store.receive_simulator_incoming, family_id, body.profile_id,
            sender, body.text.strip(), event_id, payload)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    background_tasks.add_task(_route_message, family_id, routed, intake_agent, goal_tasks, automations, family_events)
    return {"status": "received", "event_id": event_id, "message": routed.get("message")}


async def _route_message(family_id, routed, intake_agent, goal_tasks, automations, family_events):
    family_events.publish(family_id, {"type": "simulator_changed"})
    if routed["created"]:
        await intake_agent.route_received(family_id, str(routed["incoming_id"]))
    for goal_id in routed["goal_ids"]:
        await goal_tasks.start(family_id, goal_id)
        family_events.publish(family_id, {"type": "goals_changed", "goal_id": goal_id})
    await automations.recover()


@router.put("/health")
async def update_health(body: SimulatedHealth, request: Request):
    try:
        result = await asyncio.to_thread(service().update_health,
            request.state.family_id, body.child_id, body.date, body.steps, body.sleep_hours,
            body.heart_rate, body.active_energy, body.distance,
        )
        from app.main import automations
        await automations.recover()
        return result
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
