from fastapi import APIRouter, HTTPException
import httpx
from pydantic import BaseModel, Field

from plugins.oauth import OAuthConnections

router=APIRouter()


class Callback(BaseModel):
    state: str=Field(min_length=20,max_length=256)
    code: str=Field(min_length=1,max_length=4096)


@router.post('/api/plugins/{plugin_id}/authorize')
async def authorize(plugin_id: str,family_id: str):
    from app.main import task_store
    try:
        return await OAuthConnections(task_store).begin(family_id,plugin_id)
    except (ValueError,httpx.HTTPError) as error:
        raise HTTPException(400,str(error)) from error


@router.post('/api/oauth/callback')
async def callback(body: Callback):
    from app.main import task_store
    try:
        result = await OAuthConnections(task_store).finish(body.state,body.code)
        from app.plugin_service import PluginService
        await PluginService(task_store).validate(result['family_id'],result['plugin_id'])
        result['status'] = 'connected'
        return result
    except (ValueError,RuntimeError,httpx.HTTPError) as error:
        raise HTTPException(400,str(error)) from error
