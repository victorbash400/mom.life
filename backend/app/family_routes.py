from datetime import date
from io import BytesIO
from urllib.parse import quote
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError
from psycopg.errors import UniqueViolation
from starlette.responses import Response
from app.auth import families

router = APIRouter(prefix='/api/family')


class ChildWrite(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    birth_date: date | None = None
    email_updates: bool = True
    text_updates: bool = False
    notifications: bool = True


class ParentWrite(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    email: str = Field(max_length=254)


class PluginAccessWrite(BaseModel):
    profile_id: str = Field(min_length=1,max_length=100)
    enabled: bool


async def normalized_photo(file: UploadFile):
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413,'Choose a picture smaller than 5 MB.')
    try:
        with Image.open(BytesIO(content)) as image:
            if image.width * image.height > 25_000_000:
                raise ValueError()
            image.thumbnail((512,512))
            output = BytesIO()
            image.convert('RGB').save(output,format='JPEG',quality=85)
            return output.getvalue()
    except (UnidentifiedImageError,ValueError,OSError,Image.DecompressionBombError):
        raise HTTPException(400,'Choose a valid image.')


def require_child(request, identity):
    family = request.state.family_id
    if not families.child(family, identity):
        raise HTTPException(404, 'Child not found.')
    return family


@router.get('')
def family(request: Request):
    identity = request.state.family_id
    parent, children = families.snapshot(identity)
    if not parent:
        raise HTTPException(401, 'Sign in to continue.')
    for child in children:
        born = child['birth_date']
        today = date.today()
        years = today.year - born.year - ((today.month,today.day) < (born.month,born.day)) if born else None
        child.update(age=f'{years} years' if years is not None else '', color='#f4cfd5', avatarPosition='center')
    return {'id':identity,'parent':parent,'children':children}


@router.post('/children', status_code=201)
def add_child(body: ChildWrite, request: Request):
    if not body.name.strip() or body.birth_date and body.birth_date > date.today():
        raise HTTPException(400, 'Enter a name and a birth date in the past.')
    family = request.state.family_id
    identity = families.add_child(family,body.name.strip(),body.birth_date)
    families.update_child(family,identity,body.model_dump(exclude={'name','birth_date'}))
    from app.main import task_store
    from app.simulator import HEALTH_PLUGINS, SimulatorService
    if task_store.simulator_plugins(family) & HEALTH_PLUGINS:
        SimulatorService(task_store, families).seed_health(family)
    return {'id':identity}


@router.patch('/children/{identity}')
def update_child(identity: str, body: ChildWrite, request: Request):
    family = require_child(request,identity)
    if not body.name.strip() or body.birth_date and body.birth_date > date.today():
        raise HTTPException(400, 'Enter a name and a birth date in the past.')
    families.update_child(family,identity,{**body.model_dump(),'name':body.name.strip()})
    return {'id':identity}


@router.delete('/children/{identity}', status_code=204)
async def remove_child(identity: str, request: Request):
    family = require_child(request,identity)
    from app.main import task_store, goal_tasks
    for goal in task_store.list(family):
        if goal['child_id'] == identity and goal['status'] != 'completed':
            await goal_tasks.stop(goal['id'])
            task_store.set_goal_state(goal['id'],status='paused',run_state='paused',current_step='Child profile removed')
    task_store.delete_education_snapshot(family, identity)
    task_store.remove_simulator_profile(family, identity)
    task_store.remove_profile_plugin_access(family, identity)
    families.remove_child(family,identity)


@router.put('/children/{identity}/photo')
async def photo(identity: str, request: Request, file: UploadFile = File()):
    family = require_child(request,identity)
    families.update_child(family,identity,{'photo':await normalized_photo(file),'photo_type':'image/jpeg'})
    return {'id':identity}


@router.get('/children/{identity}/photo')
def get_photo(identity: str, request: Request):
    child = families.child(request.state.family_id,identity)
    if not child:
        raise HTTPException(404,'Child not found.')
    if not child['photo']:
        raise HTTPException(404,'No photo uploaded.')
    return Response(bytes(child['photo']),media_type=child['photo_type'] or 'image/jpeg')


@router.put('/parent/photo')
async def parent_photo(request: Request, file: UploadFile = File()):
    family = request.state.family_id
    if not families.update_parent_photo(family,await normalized_photo(file),'image/jpeg'):
        raise HTTPException(404,'Parent profile not found.')
    return {'id':family}


@router.patch('/parent')
def update_parent(body: ParentWrite, request: Request):
    name = body.name.strip()
    email = body.email.strip().lower()
    if not name or email.count('@') != 1 or '.' not in email.split('@')[-1] or any(char.isspace() for char in email):
        raise HTTPException(400,'Enter a name and valid email.')
    try:
        if not families.update_parent(request.state.family_id,name,email):
            raise HTTPException(404,'Parent profile not found.')
    except UniqueViolation:
        raise HTTPException(409,'An account with this email already exists.')
    return {'id':request.state.family_id}


@router.get('/parent/photo')
def get_parent_photo(request: Request):
    photo = families.parent_photo(request.state.family_id)
    if not photo or not photo['photo']:
        raise HTTPException(404,'No photo uploaded.')
    return Response(bytes(photo['photo']),media_type=photo['photo_type'] or 'image/jpeg')


@router.get('/plugin-access')
def plugin_access(request: Request):
    from app.main import task_store
    from plugins.catalog import plugin_by_id
    plugin_ids, access = task_store.profile_plugin_access(request.state.family_id)
    return {'sources': [
        {'id':plugin_id,'name':plugin_by_id(plugin_id).name,'profiles':{
            profile_id:enabled for (profile_id,access_plugin),enabled in access.items() if access_plugin == plugin_id
        }} for plugin_id in plugin_ids
    ]}


@router.patch('/plugin-access/{plugin_id}')
def update_plugin_access(plugin_id: str, body: PluginAccessWrite, request: Request):
    from app.main import task_store
    from plugins.catalog import plugin_by_id
    try:
        plugin_by_id(plugin_id)
    except ValueError as error:
        raise HTTPException(404,str(error)) from error
    family = request.state.family_id
    if body.profile_id != 'parent' and not families.child(family,body.profile_id):
        raise HTTPException(404,'Profile not found.')
    if not task_store.set_profile_plugin_access(family,body.profile_id,plugin_id,body.enabled):
        raise HTTPException(409,'This source is not connected.')
    return {'id':plugin_id,'profile_id':body.profile_id,'enabled':body.enabled}


def require_owner(request, identity):
    return request.state.family_id if identity == 'parent' else require_child(request,identity)


@router.get('/children/{identity}/nodes')
def nodes(identity: str, request: Request):
    return families.nodes(require_owner(request,identity),identity)


class FolderWrite(BaseModel):
    name: str = Field(min_length=1,max_length=180)
    parent_id: str | None = None


@router.post('/children/{identity}/folders', status_code=201)
def folder(identity: str, body: FolderWrite, request: Request):
    family = require_owner(request,identity)
    if not body.name.strip():
        raise HTTPException(400,'Enter a folder name.')
    try:
        return {'id':families.add_node(family,identity,body.parent_id,body.name.strip())}
    except (ValueError,UniqueViolation):
        raise HTTPException(409,'Folder is missing or this name already exists.')


@router.post('/children/{identity}/files', status_code=201)
async def upload(identity: str, request: Request, file: UploadFile = File(), parent_id: str | None = Form(None)):
    family = require_owner(request,identity)
    content = await file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413,'Choose a file smaller than 10 MB.')
    name = (file.filename or 'File').replace('\\','/').split('/')[-1].strip()[:180]
    if not name:
        raise HTTPException(400,'A filename is required.')
    media_type = file.content_type or 'application/octet-stream'
    try:
        node_id = families.add_node(family,identity,parent_id,name,content,media_type)
    except (ValueError,UniqueViolation):
        raise HTTPException(409,'Folder is missing or this name already exists.')
    from app.incoming_content import extract_upload_text
    from app.main import intake_agent
    await intake_agent.receive(
        family,
        'upload',
        node_id,
        correlation=node_id,
        sender='Mom',
        subject=name,
        content=extract_upload_text(content,media_type,name),
        payload={'node_id':node_id,'child_id':identity,'parent_id':parent_id,'filename':name,'media_type':media_type},
    )
    return {'id':node_id}


@router.get('/children/{identity}/files/{node_id}')
def download(identity: str, node_id: str, request: Request):
    node = families.node(require_owner(request,identity),identity,node_id)
    if not node or node['kind'] != 'file':
        raise HTTPException(404,'File not found.')
    return Response(bytes(node['content']),media_type='application/octet-stream',headers={'Content-Disposition':f"attachment; filename*=UTF-8''{quote(node['name'],safe='')}",'X-Content-Type-Options':'nosniff'})


@router.delete('/children/{identity}/nodes/{node_id}', status_code=204)
def delete_node(identity: str, node_id: str, request: Request):
    if not families.remove_node(require_owner(request,identity),identity,node_id):
        raise HTTPException(404,'File or folder not found.')


@router.get('/children/{identity}/avatar')
def avatar(identity: str, request: Request):
    import hashlib
    family = require_child(request,identity)
    child = families.child(family,identity)
    seed = hashlib.sha256(child['avatar_seed'].encode()).digest()
    colors = ['#d9caef','#c7e2db','#f4cfd5','#ead9b5']
    color = colors[seed[0] % len(colors)]
    # Self-contained abstract SVG; no child data leaves the application.
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="50" fill="{color}"/><circle cx="50" cy="39" r="19" fill="#fff8ed"/><path d="M17 94 Q18 64 50 64 Q82 64 83 94" fill="#fff8ed"/><circle cx="44" cy="39" r="2" fill="#65514a"/><circle cx="56" cy="39" r="2" fill="#65514a"/><path d="M44 48 Q50 52 56 48" fill="none" stroke="#ac665d" stroke-width="2" stroke-linecap="round"/></svg>'
    return Response(svg,media_type='image/svg+xml',headers={'Content-Security-Policy':"default-src 'none'; style-src 'none'; sandbox"})
