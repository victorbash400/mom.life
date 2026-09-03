from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    family_id: str = Field(min_length=1, max_length=128)
    chat_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=20_000)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ModelResponse(BaseModel):
    id: str
    purpose: str
    enabled: bool


class RuntimeResponse(BaseModel):
    region: str
    project_id: str
    models: list[ModelResponse]


class TaskCreate(BaseModel):
    family_id: str = Field(min_length=1, max_length=128)
    child_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=2_000)


class TaskUpdate(BaseModel):
    status: Literal["active", "paused", "completed"]
