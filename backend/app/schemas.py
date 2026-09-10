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


class PluginPermissionUpdate(BaseModel):
    permission_id: str = Field(min_length=1, max_length=160)
    enabled: bool


class GoalRevision(BaseModel):
    instruction: str = Field(min_length=1,max_length=20000)


class QuestionAnswer(BaseModel):
    answer: str = Field(min_length=1,max_length=20000)
    approved: bool = False


class IntakeRetry(BaseModel):
    guidance: str = Field(default="", max_length=20_000)


class SecuritySettingsWrite(BaseModel):
    enabled: bool = True
    alert_level: Literal["urgent", "important", "all"] = "important"
    instructions: str = Field(default="", max_length=4_000)


class CalendarPreferencesWrite(BaseModel):
    enabled: bool = True
    reminder_method: Literal["popup", "email"] = "popup"
    reminder_minutes: Literal[10, 30, 60, 1440] = 30


class SkillWrite(BaseModel):
    name: str = Field(min_length=1,max_length=120)
    description: str = Field(min_length=1,max_length=1000)
    instructions: str = Field(min_length=1,max_length=20000)
    required_plugin_ids: list[str] = Field(default_factory=list)
