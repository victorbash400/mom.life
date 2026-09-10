from datetime import date
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.provider_events import ProviderEvents
from app.simulator import SimulatorService


router = APIRouter(prefix="/api/simulator")


class SimulatedMessage(BaseModel):
    profile_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=4000)


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
async def send_message(body: SimulatedMessage, request: Request):
    from app.auth import families
    from app.main import family_events, goal_tasks, intake_agent, task_store
    family_id = request.state.family_id
    if "whatsapp" not in task_store.simulator_plugins(family_id):
        raise HTTPException(409, "Connect WhatsApp Simulator first.")
    profile = families.profile(family_id) if body.profile_id == "parent" else families.child(family_id, body.profile_id)
    if not profile:
        raise HTTPException(404, "Simulated family profile not found.")
    event_id = f"sim-wa-{uuid4()}"
    payload = {"id": event_id, "from": f"sim:{body.profile_id}", "text": {"body": body.text.strip()}, "simulated": True, "profile_id": body.profile_id}
    received = ProviderEvents(task_store).receive_with_status(family_id, "whatsapp", event_id, f"sim:{body.profile_id}", payload)
    task_store.add_simulator_message(family_id, body.profile_id, "incoming", body.text.strip(), event_id)
    if not received["matched"] and not received["duplicate"]:
        await intake_agent.receive(
            family_id, "whatsapp", event_id, correlation=f"sim:{body.profile_id}", sender=f"{profile['name']} (Simulator)",
            content=body.text.strip(), payload=payload,
        )
    for goal_id in received["goal_ids"]:
        await goal_tasks.start(family_id, goal_id)
        family_events.publish(family_id, {"type": "goals_changed", "goal_id": goal_id})
    return {"status": "received", "event_id": event_id}


@router.put("/health")
def update_health(body: SimulatedHealth, request: Request):
    try:
        return service().update_health(request.state.family_id, **body.model_dump())
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
