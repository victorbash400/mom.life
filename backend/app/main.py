import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from .chat_stream import stream_agent_events
from .config import get_settings
from .event_stream import family_events
from .goal_tasks import GoalTaskManager
from .model_catalog import configured_models
from .schemas import ChatRequest, HealthResponse, ModelResponse, PluginPermissionUpdate, RuntimeResponse, TaskCreate, TaskUpdate
from .task_store import TaskStore
from plugins.catalog import PLUGINS, plugin_by_id, plugin_snapshot


@asynccontextmanager
async def lifespan(app):
    task_store.recover()
    try:
        yield
    finally:
        await goal_tasks.shutdown()


app = FastAPI(title="mom.life API", version="0.1.0", lifespan=lifespan)
from app.auth import router as auth_router, require_session
app.include_router(auth_router)
from app.family_routes import router as family_router
app.include_router(family_router)
from app.chat_routes import router as chat_router
app.include_router(chat_router)
app.middleware("http")(require_session)
from app.goal_routes import router as goal_router
app.include_router(goal_router)
from app.whatsapp_webhook import router as webhook_router
app.include_router(webhook_router)
from app.oauth_routes import router as oauth_router
app.include_router(oauth_router)
settings = get_settings()
task_store = TaskStore(settings.database_url)
goal_tasks = GoalTaskManager(task_store)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT"],
    allow_headers=["Content-Type"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.get("/api/runtime", response_model=RuntimeResponse)
def runtime() -> RuntimeResponse:
    models = configured_models(
        active_id=settings.strands_model_id,
        reasoning_id=settings.reasoning_model_id,
        voice_id=settings.voice_model_id,
    )
    return RuntimeResponse(
        region=settings.strands_region,
        project_id=settings.bedrock_project_id,
        models=[ModelResponse(id=model.id, purpose=model.purpose, enabled=model.enabled) for model in models],
    )


@app.post("/api/chat/stream")
def chat_stream(body: ChatRequest) -> StreamingResponse:
    from app.chat_routes import chats
    if not chats.get(body.family_id, body.chat_id):
        raise HTTPException(404, "Chat not found.")
    return StreamingResponse(
        stream_agent_events(family_id=body.family_id, chat_id=body.chat_id, message=body.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/tasks")
def list_tasks(family_id: str) -> list[dict[str, object]]:
    return task_store.list(family_id)


@app.post("/api/tasks", status_code=201)
async def create_task(body: TaskCreate) -> dict[str, object]:
    from app.auth import families
    if body.child_id != 'all' and not families.child(body.family_id,body.child_id):
        raise HTTPException(404,"Child not found.")
    goal = task_store.create(body.family_id, body.child_id, body.text)
    await goal_tasks.start(body.family_id, str(goal["id"]))
    return goal


@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, body: TaskUpdate, family_id: str) -> dict[str, object]:
    current = task_store.get(family_id,task_id)
    if not current:
        raise HTTPException(404,"Task not found")
    if body.status == "active" and current['child_id'] != 'all':
        from app.auth import families
        if not families.child(family_id,current['child_id']):
            raise HTTPException(409,"This child's profile has been removed.")
    if body.status == "completed":
        raise HTTPException(409,"Assignments must complete with evidence before the goal can finish.")
    if body.status == "paused":
        await goal_tasks.stop(task_id)
    task = task_store.update(task_id, body.status)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if body.status == "active":
        await goal_tasks.start(str(task["family_id"]), task_id)
    family_events.publish(str(task["family_id"]), {"type": "goals_changed", "goal_id": task_id})
    return task


@app.delete("/api/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str, family_id: str) -> None:
    if not task_store.get(family_id,task_id):
        raise HTTPException(404,"Task not found")
    await goal_tasks.stop(task_id)
    from app.browser_cleanup import discard_goal_browser_sessions
    await discard_goal_browser_sessions(task_store,task_id)
    if not task_store.delete(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    family_events.publish(family_id,{"type":"goals_changed","goal_id":task_id})


@app.get("/api/tasks/events")
def task_events(family_id: str) -> StreamingResponse:
    async def stream():
        queue = family_events.subscribe(family_id)
        try:
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            raise
        finally:
            family_events.unsubscribe(family_id, queue)
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/plugins")
def list_plugins(family_id: str) -> dict[str, object]:
    from app.plugin_service import PluginService
    return {"plugins": PluginService(task_store).list(family_id)}


@app.post("/api/plugins/{plugin_id}")
def install_plugin(plugin_id: str, family_id: str) -> dict[str, object]:
    try:
        plugin = plugin_by_id(plugin_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error
    task_store.install_plugin(family_id, plugin_id)
    return plugin_snapshot(plugin, True, task_store.permissions(family_id, plugin_id))


@app.delete("/api/plugins/{plugin_id}", status_code=204)
def uninstall_plugin(plugin_id: str, family_id: str) -> None:
    try:
        plugin_by_id(plugin_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error
    task_store.uninstall_plugin(family_id, plugin_id)


@app.patch("/api/plugins/{plugin_id}/permissions")
def update_plugin_permission(plugin_id: str, family_id: str, body: PluginPermissionUpdate) -> dict[str, object]:
    try:
        plugin = plugin_by_id(plugin_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error
    valid = {f"{plugin.id}.{index}" for index, _ in enumerate(plugin.permissions)}
    if body.permission_id not in valid:
        raise HTTPException(400, "Unknown plugin permission.")
    task_store.set_permission(family_id, plugin_id, body.permission_id, body.enabled)
    return plugin_snapshot(plugin, plugin_id in task_store.installed_plugins(family_id), task_store.permissions(family_id, plugin_id))


@app.get("/api/skills")
def list_skills(family_id: str) -> dict[str, object]:
    from .skills import BUILTIN_SKILLS
    task_store.seed_skills(family_id, BUILTIN_SKILLS)
    return {"skills": task_store.skills(family_id)}


@app.post("/api/plugins/{plugin_id}/validate")
async def validate_plugin(plugin_id: str, family_id: str):
    from app.plugin_service import PluginService
    try:
        return await PluginService(task_store).validate(family_id,plugin_id)
    except Exception as error:
        raise HTTPException(400,str(error)) from error
