from fastapi import APIRouter, HTTPException, Request
from app.chat_sessions import ChatSessions
from app.config import get_settings

router = APIRouter(prefix='/api/chats')
settings = get_settings()
chats = ChatSessions(
    database=settings.database_url if settings.uses_agentcore_runtime else "",
    memory_id=settings.agentcore_memory_id,
    region=settings.strands_region,
)


@router.get('')
def list_chats(request: Request):
    return chats.list(request.state.family_id)


@router.post('', status_code=201)
def create_chat(request: Request):
    return chats.create(request.state.family_id)


@router.get('/{identity}')
def get_chat(identity: str, request: Request):
    chat = chats.get(request.state.family_id, identity)
    if not chat:
        raise HTTPException(404, 'Chat not found.')
    return chat


@router.delete('/{identity}', status_code=204)
def delete_chat(identity: str, request: Request):
    if not chats.delete(request.state.family_id, identity):
        raise HTTPException(404, 'Chat not found.')
