from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from .chat_stream import stream_agent_events
from .config import get_settings
from .model_catalog import configured_models
from .schemas import ChatRequest, HealthResponse, ModelResponse, RuntimeResponse


app = FastAPI(title="mom.life API", version="0.1.0")
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
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
    return StreamingResponse(
        stream_agent_events(family_id=body.family_id, chat_id=body.chat_id, message=body.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
