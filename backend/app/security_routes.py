from fastapi import APIRouter, HTTPException, Request

from app.event_stream import family_events
from app.schemas import SecuritySettingsWrite


router = APIRouter(prefix="/api/security")


def services():
    from app.main import security_agent, task_store
    return task_store, security_agent


@router.get("")
def security(request: Request) -> dict[str, object]:
    store, _ = services()
    return {"settings": store.security_settings(request.state.family_id), "reviews": store.security_reviews(request.state.family_id)}


@router.patch("/settings")
def update_settings(body: SecuritySettingsWrite, request: Request) -> dict[str, object]:
    store, _ = services()
    settings = store.update_security_settings(request.state.family_id, body.enabled, body.alert_level, body.instructions)
    family_events.publish(request.state.family_id, {"type": "security_changed"})
    return settings


@router.post("/reviews/{review_id}/retry")
async def retry(review_id: str, request: Request) -> dict[str, object]:
    store, manager = services()
    if not store.security_review(review_id, request.state.family_id):
        raise HTTPException(404, "Security review not found.")
    return await manager.retry(request.state.family_id, review_id)


@router.post("/reviews/{review_id}/dismiss")
def dismiss(review_id: str, request: Request) -> dict[str, bool]:
    store, _ = services()
    if not store.dismiss_security_alert(request.state.family_id, review_id):
        raise HTTPException(404, "Security alert not found.")
    family_events.publish(request.state.family_id, {"type": "security_changed", "review_id": review_id})
    return {"dismissed": True}
