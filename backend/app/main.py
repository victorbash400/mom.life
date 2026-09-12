import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
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
    await asyncio.to_thread(task_store.initialize)

    async def recover():
        await asyncio.to_thread(task_store.recover)
        automations.start_listener()
        await asyncio.gather(
            security_agent.recover(),
            education_agent.recover(),
            intake_agent.recover(),
        )

    recovery = asyncio.create_task(recover(), name="mom-life-recovery")
    try:
        yield
    finally:
        recovery.cancel()
        await asyncio.gather(recovery, return_exceptions=True)
        await automations.shutdown()
        await intake_agent.shutdown()
        await security_agent.shutdown()
        await education_agent.shutdown()
        await goal_tasks.shutdown()


app = FastAPI(title="mom.life API", version="0.1.0", lifespan=lifespan)
from app.auth import families, router as auth_router, require_session
app.include_router(auth_router)
from app.family_routes import router as family_router
app.include_router(family_router)
from app.chat_routes import router as chat_router
app.include_router(chat_router)
app.middleware("http")(require_session)
from app.goal_routes import router as goal_router
app.include_router(goal_router)
from app.intake_routes import router as intake_router
app.include_router(intake_router)
from app.security_routes import router as security_router
app.include_router(security_router)
from app.education_routes import router as education_router
app.include_router(education_router)
from app.calendar_routes import router as calendar_router
app.include_router(calendar_router)
from app.whatsapp_webhook import router as webhook_router
app.include_router(webhook_router)
from app.apple_health_routes import router as apple_health_router
app.include_router(apple_health_router)
from app.simulator_routes import router as simulator_router
app.include_router(simulator_router)
from app.oauth_routes import router as oauth_router
app.include_router(oauth_router)
from app.automation_routes import router as automation_router
app.include_router(automation_router)
settings = get_settings()
task_store = TaskStore(settings.database_url)
goal_tasks = GoalTaskManager(task_store)
from app.automation_manager import AutomationManager
automations = AutomationManager(task_store,goal_tasks)
from app.security_agent import SecurityAgentManager
security_agent = SecurityAgentManager(task_store)
from app.education_agent import EducationAgentManager
education_agent = EducationAgentManager(task_store)
from app.intake_agent import IntakeAgentManager
intake_agent = IntakeAgentManager(task_store, goal_tasks, security_agent, education_agent)
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
def chat_stream(body: ChatRequest, request: Request) -> StreamingResponse:
    from app.chat_routes import chats
    family_id = request.state.family_id
    chats.ensure(family_id, body.chat_id)
    return StreamingResponse(
        stream_agent_events(family_id=family_id, chat_id=body.chat_id, message=body.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/tasks")
def list_tasks(request: Request) -> list[dict[str, object]]:
    return task_store.list(request.state.family_id)


@app.post("/api/tasks", status_code=201)
async def create_task(body: TaskCreate, background_tasks: BackgroundTasks, request: Request) -> dict[str, object]:
    from app.auth import families
    family_id = request.state.family_id
    if body.child_id != 'all' and not families.child(family_id,body.child_id):
        raise HTTPException(404,"Child not found.")
    goal = task_store.create(family_id, body.child_id, body.text)
    background_tasks.add_task(goal_tasks.start, family_id, str(goal["id"]), known_active=True)
    return goal


@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, body: TaskUpdate, request: Request) -> dict[str, object]:
    family_id = request.state.family_id
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
        for item in automations.store.list(family_id):
            if item["goal_id"] == task_id:
                await automations._stop_runs(item["id"])
    task = task_store.update(task_id, body.status)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if body.status == "active":
        await goal_tasks.start(str(task["family_id"]), task_id)
        automations.kick(family_id,task_id)
    family_events.publish(str(task["family_id"]), {"type": "goals_changed", "goal_id": task_id})
    return task


@app.delete("/api/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str, request: Request) -> None:
    family_id = request.state.family_id
    if not task_store.get(family_id,task_id):
        raise HTTPException(404,"Task not found")
    await goal_tasks.stop(task_id)
    for item in automations.store.list(family_id):
        if item["goal_id"] == task_id:
            await automations.delete(family_id,item["id"])
    from app.browser_cleanup import discard_goal_browser_sessions
    await discard_goal_browser_sessions(task_store,task_id)
    if not task_store.delete(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    family_events.publish(family_id,{"type":"goals_changed","goal_id":task_id})


@app.get("/api/tasks/events")
def task_events(request: Request) -> StreamingResponse:
    family_id = request.state.family_id
    async def stream():
        queue = family_events.subscribe(family_id)
        try:
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20)
                    yield f"data: {json.dumps(event)}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            raise
        finally:
            family_events.unsubscribe(family_id, queue)
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/plugins")
def list_plugins(request: Request) -> dict[str, object]:
    from app.plugin_service import PluginService
    return {"plugins": PluginService(task_store).list(request.state.family_id)}


@app.post("/api/plugins/{plugin_id}")
def install_plugin(plugin_id: str, request: Request) -> dict[str, object]:
    try:
        plugin = plugin_by_id(plugin_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error
    permissions = task_store.install_plugin(request.state.family_id, plugin_id)
    return plugin_snapshot(plugin, True, permissions)


@app.delete("/api/plugins/{plugin_id}", status_code=204)
def uninstall_plugin(plugin_id: str, request: Request) -> None:
    try:
        plugin_by_id(plugin_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error
    task_store.uninstall_plugin(request.state.family_id, plugin_id)


@app.patch("/api/plugins/{plugin_id}/permissions")
def update_plugin_permission(plugin_id: str, body: PluginPermissionUpdate, request: Request) -> dict[str, object]:
    try:
        plugin = plugin_by_id(plugin_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error
    valid = {f"{plugin.id}.{index}" for index, _ in enumerate(plugin.permissions)}
    if body.permission_id not in valid:
        raise HTTPException(400, "Unknown plugin permission.")
    family_id = request.state.family_id
    task_store.set_permission(family_id, plugin_id, body.permission_id, body.enabled)
    return plugin_snapshot(plugin, plugin_id in task_store.installed_plugins(family_id), task_store.permissions(family_id, plugin_id))


@app.get("/api/skills")
def list_skills(request: Request) -> dict[str, object]:
    from .skills import BUILTIN_SKILLS
    family_id = request.state.family_id
    task_store.seed_skills(family_id, BUILTIN_SKILLS)
    return {"skills": task_store.skills(family_id)}


@app.post("/api/plugins/{plugin_id}/validate")
async def validate_plugin(plugin_id: str, request: Request):
    from app.plugin_service import PluginService
    try:
        return await PluginService(task_store).validate(request.state.family_id,plugin_id)
    except Exception as error:
        raise HTTPException(400,str(error)) from error
