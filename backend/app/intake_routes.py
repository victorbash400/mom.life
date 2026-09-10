from fastapi import APIRouter, HTTPException, Request

from app.schemas import IntakeRetry


router = APIRouter()


def services():
    from app.main import intake_agent, task_store
    return task_store, intake_agent


@router.get('/api/incoming')
def incoming_items(request: Request) -> list[dict[str, object]]:
    store, _ = services()
    return store.incoming_items(request.state.family_id)


@router.post('/api/incoming/{incoming_id}/retry')
async def retry_incoming(incoming_id: str, body: IntakeRetry, request: Request) -> dict[str, object]:
    store, manager = services()
    if not store.incoming(incoming_id, request.state.family_id):
        raise HTTPException(404, 'Incoming item not found.')
    try:
        return await manager.retry(request.state.family_id, incoming_id, body.guidance)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@router.delete('/api/incoming/{incoming_id}', status_code=204)
async def delete_incoming(incoming_id: str, request: Request) -> None:
    store, manager = services()
    if not store.incoming(incoming_id, request.state.family_id):
        raise HTTPException(404, 'Incoming item not found.')
    from app.main import education_agent, security_agent
    with store._connect() as connection:
        security = connection.execute("SELECT id FROM security_reviews WHERE incoming_id=? AND family_id=?", (incoming_id, request.state.family_id)).fetchone()
        education = connection.execute("SELECT id FROM education_reviews WHERE incoming_id=? AND family_id=?", (incoming_id, request.state.family_id)).fetchone()
    await manager.stop(incoming_id)
    if security:
        await security_agent.stop(str(security["id"]))
    if education:
        await education_agent.stop(str(education["id"]))
    if not store.delete_incoming(request.state.family_id, incoming_id):
        raise HTTPException(404, 'Incoming item not found.')
