from dataclasses import dataclass


@dataclass(frozen=True)
class ModelDefinition:
    id: str
    purpose: str
    enabled: bool


def configured_models(*, active_id: str, reasoning_id: str, voice_id: str) -> tuple[ModelDefinition, ...]:
    return (
        ModelDefinition(id=active_id, purpose="family agent", enabled=True),
        ModelDefinition(id=reasoning_id, purpose="future complex reasoning", enabled=False),
        ModelDefinition(id=voice_id, purpose="future realtime voice", enabled=False),
    )
