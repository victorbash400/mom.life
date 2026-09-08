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
    await manager.stop(incoming_id)
    if not store.delete_incoming(request.state.family_id, incoming_id):
        raise HTTPException(404, 'Incoming item not found.')
