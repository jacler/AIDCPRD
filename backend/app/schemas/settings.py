from enum import Enum

from pydantic import BaseModel, Field

from app.data.consultation_prompt_presets import (
    DEFAULT_PRESET_ID,
    PRESET_BY_ID,
    PromptPreset,
)


class ConsultationProvider(str, Enum):
    RULE = "rule"
    OPENAI_COMPATIBLE = "openai_compatible"


CONSULTATION_SETTINGS_KEY = "consultation"

_DEFAULT_PROMPT = PRESET_BY_ID[DEFAULT_PRESET_ID].prompt

DEFAULT_CONSULTATION_SETTINGS: dict = {
    "enabled": True,
    "provider": ConsultationProvider.RULE.value,
    "api_base_url": "https://api.openai.com/v1",
    "api_key": "",
    "model": "gpt-4o-mini",
    "timeout_seconds": 60,
    "system_prompt_preset_id": DEFAULT_PRESET_ID,
    "system_prompt": _DEFAULT_PROMPT,
}


class PromptPresetRead(BaseModel):
    id: str
    name: str
    description: str
    guided_steps: list[str]
    editable: bool = False


class ConsultationSettingsRead(BaseModel):
    enabled: bool = True
    provider: ConsultationProvider = ConsultationProvider.RULE
    api_base_url: str = "https://api.openai.com/v1"
    api_key_configured: bool = False
    model: str = "gpt-4o-mini"
    timeout_seconds: int = Field(default=60, ge=5, le=300)
    system_prompt_preset_id: str = DEFAULT_PRESET_ID
    system_prompt: str = _DEFAULT_PROMPT
    chat_endpoint: str = "/api/v1/consultation/chat"


class ConsultationSettingsUpdate(BaseModel):
    enabled: bool | None = None
    provider: ConsultationProvider | None = None
    api_base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    timeout_seconds: int | None = Field(default=None, ge=5, le=300)
    system_prompt_preset_id: str | None = None
    system_prompt: str | None = None


def preset_to_read(preset: PromptPreset) -> PromptPresetRead:
    return PromptPresetRead(
        id=preset.id,
        name=preset.name,
        description=preset.description,
        guided_steps=preset.guided_steps,
        editable=preset.editable,
    )


class ConsultationTestRequest(BaseModel):
    message: str = Field(default="为医院提供10P算力", min_length=1, max_length=500)


class ConsultationTestResponse(BaseModel):
    success: bool
    message: str
    provider: ConsultationProvider
