import json
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


@router.get("/summary")
def security_summary(request: Request) -> dict[str, int]:
    store, _ = services()
    return {"alert_count": store.security_alert_count(request.state.family_id)}


@router.patch("/settings")
def update_settings(body: SecuritySettingsWrite, request: Request) -> dict[str, object]:
    store, _ = services()
    from app.auth import families
    if any(not families.child(request.state.family_id,identity) for identity in body.child_ids):
        raise HTTPException(400,'Choose children belonging to this family.')
    settings = store.update_security_settings(request.state.family_id, **body.model_dump())
    family_events.publish(request.state.family_id, {"type": "security_changed"})
    return settings


@router.post("/check", status_code=202)
async def check(request: Request):
    store, manager = services()
    settings = store.security_settings(request.state.family_id)
    if not settings['enabled']:
        raise HTTPException(409, 'Enable safety monitoring before checking.')
    count = 0
    with store._connect() as db:
        rows = db.execute('SELECT id,source,payload,child_id FROM incoming_items WHERE family_id=? ORDER BY created_at DESC LIMIT 50', (request.state.family_id,)).fetchall()
    for row in rows:
        item = {**dict(row),'payload':json.loads(row['payload'])}
        if store.security_scope_matches(settings,item):
            _, created = await manager.receive(request.state.family_id,item['id'],manual=True)
            count += int(created)
            if count == 10:
                break
    return {'queued':count}


@router.post("/reviews/{review_id}/retry")
async def retry(review_id: str, request: Request) -> dict[str, object]:
    store, manager = services()
    if not store.security_review(review_id, request.state.family_id):
        raise HTTPException(404, "Safety review not found.")
    return await manager.retry(request.state.family_id, review_id)


@router.post("/reviews/{review_id}/dismiss")
def dismiss(review_id: str, request: Request) -> dict[str, bool]:
    store, _ = services()
    if not store.dismiss_security_alert(request.state.family_id, review_id):
        raise HTTPException(404, "Safety alert not found.")
    family_events.publish(request.state.family_id, {"type": "security_changed", "review_id": review_id})
    return {"dismissed": True}
