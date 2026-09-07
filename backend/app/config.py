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
    bedrock_project_id: str = "proj_t6e6u24fw7kbzz5otsfo"
    aws_profile: str = Field(default="", validation_alias=AliasChoices("MOM_LIFE_AWS_PROFILE", "AWS_PROFILE"))
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / "backend" / ".env",
        env_prefix="MOM_LIFE_",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
