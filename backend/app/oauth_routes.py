from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from plugins.oauth import OAuthConnections

router=APIRouter()


class Callback(BaseModel):
    state: str=Field(min_length=20,max_length=256)
    code: str=Field(min_length=1,max_length=4096)


@router.post('/api/plugins/{plugin_id}/authorize')
def authorize(plugin_id: str,family_id: str):
    from app.main import task_store
    try:
        return OAuthConnections(task_store).begin(family_id,plugin_id)
    except ValueError as error:
        raise HTTPException(400,str(error)) from error


@router.post('/api/oauth/callback')
async def callback(body: Callback):
    from app.main import task_store
    try:
        return await OAuthConnections(task_store).finish(body.state,body.code)
    except ValueError as error:
        raise HTTPException(400,str(error)) from error
