from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix='/api/automations')

class AutomationCreate(BaseModel):
    goal_id: str
    instruction: str = Field(min_length=1,max_length=4000)
    trigger: Literal['time','health','incoming']
    schedule: str = Field(default='',max_length=200)
    timezone: str = Field(default='UTC',max_length=100)

class AutomationUpdate(BaseModel):
    instruction: str | None = Field(default=None,min_length=1,max_length=4000)
    enabled: bool | None = None
    schedule: str | None = Field(default=None,max_length=200)
    timezone: str | None = Field(default=None,max_length=100)

def service():
    from app.main import automations
    return automations

@router.get('')
def list_automations(request: Request):
    manager = service()
    from app.config import get_settings
    settings = get_settings()
    return {'automations':manager.store.list(request.state.family_id),
            'notifications':manager.store.notifications(request.state.family_id),
            'scheduler_ready':bool(settings.automation_target_arn and settings.automation_role_arn),
            'events_connected':manager.events_connected}

@router.post('',status_code=201)
async def create_automation(body: AutomationCreate, request: Request):
    try:
        return await service().create(request.state.family_id,**body.model_dump())
    except ValueError as error:
        raise HTTPException(400,str(error)) from error

@router.patch('/{identity}')
async def update_automation(identity: str, body: AutomationUpdate, request: Request):
    try:
        return await service().update(request.state.family_id,identity,**body.model_dump(exclude_none=True))
    except ValueError as error:
        raise HTTPException(400,str(error)) from error

@router.delete('/{identity}',status_code=204)
async def delete_automation(identity: str, request: Request):
    try:
        await service().delete(request.state.family_id,identity)
    except ValueError as error:
        raise HTTPException(404,str(error)) from error

@router.post('/{identity}/run',status_code=202)
async def check_now(identity: str, request: Request):
    from uuid import uuid4
    manager = service()
    item = manager.store.get(request.state.family_id,identity)
    if not item:
        raise HTTPException(404,'Automation not found.')
    if not manager.store.enqueue(identity,item['version'],str(uuid4()),{'source':'manual_check'}):
        raise HTTPException(409,'Resume this automation and its task before checking.')
    manager.kick(request.state.family_id,item['goal_id'])
    manager.publish(request.state.family_id)
    return {'status':'queued'}

@router.get('/{identity}/runs')
def list_runs(identity: str, request: Request):
    manager = service()
    if not manager.store.get(request.state.family_id,identity):
        raise HTTPException(404,'Automation not found.')
    with manager.tasks._connect() as db:
        rows = db.execute('SELECT * FROM automation_wakes WHERE automation_id=? ORDER BY created_at DESC LIMIT 10', (identity,)).fetchall()
    return [{**dict(row),'task':manager.tasks.get(request.state.family_id,row['run_goal_id']) if row['run_goal_id'] else None} for row in rows]

@router.post('/notifications/{identity}/read',status_code=204)
def read_notification(identity: str, request: Request):
    from app.task_store import now
    with service().tasks._connect() as db:
        changed = db.execute('UPDATE automation_notifications SET read_at=? WHERE id=? AND family_id=?',
                             (now(),identity,request.state.family_id)).rowcount
    if not changed:
        raise HTTPException(404,'Notification not found.')
    service().publish(request.state.family_id)
