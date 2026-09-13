from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str = ""
    strands_region: str = "us-east-1"
    strands_model_id: str = "moonshotai.kimi-k2.5"
    reasoning_model_id: str = "openai.gpt-5.6-luna"
    voice_model_id: str = "amazon.nova-2-sonic-v1:0"
    model_timeout_seconds: int = 60
    model_service_tier: str = "priority"
    model_max_tokens: int = 2048
    bedrock_project_id: str = "proj_t6e6u24fw7kbzz5otsfo"
    aws_profile: str = Field(default="", validation_alias=AliasChoices("MOM_LIFE_AWS_PROFILE", "AWS_PROFILE"))
    automation_target_arn: str = ''
    automation_role_arn: str = ''
    automation_dlq_arn: str = ''
    automation_schedule_group: str = 'mom-life'
    cors_origins: str = "http://localhost:3000"
    agentcore_runtime_arn: str = ""
    agentcore_runtime_qualifier: str = "DEFAULT"
    agentcore_memory_id: str = ""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / "backend" / ".env",
        env_prefix="MOM_LIFE_",
        extra="ignore",
    )

    @property
    def model_request_fields(self) -> dict:
        if self.strands_model_id == "moonshotai.kimi-k2.5":
            return {"thinking": {"type": "disabled"}}
        return {}

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def uses_agentcore_runtime(self) -> bool:
        return bool(self.agentcore_runtime_arn)


@lru_cache
def get_settings() -> Settings:
    return Settings()
