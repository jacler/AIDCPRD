from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.repositories.app_settings_repository import AppSettingsRepository
from app.data.consultation_prompt_presets import CONSULTATION_PROMPT_PRESETS
from app.schemas.settings import (
    ConsultationSettingsRead,
    ConsultationSettingsUpdate,
    ConsultationTestRequest,
    ConsultationTestResponse,
    PromptPresetRead,
    preset_to_read,
)
from app.services.consultation_config import ConsultationConfigService

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/consultation/prompt-presets", response_model=list[PromptPresetRead])
async def list_consultation_prompt_presets(
    _: User = Depends(get_current_user),
) -> list[PromptPresetRead]:
    return [preset_to_read(p) for p in CONSULTATION_PROMPT_PRESETS]


@router.get("/consultation", response_model=ConsultationSettingsRead)
async def get_consultation_settings(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsultationSettingsRead:
    service = ConsultationConfigService(AppSettingsRepository(db))
    return await service.get_settings()


@router.put("/consultation", response_model=ConsultationSettingsRead)
async def update_consultation_settings(
    payload: ConsultationSettingsUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ConsultationSettingsRead:
    service = ConsultationConfigService(AppSettingsRepository(db))
    return await service.update_settings(payload)


@router.post("/consultation/test", response_model=ConsultationTestResponse)
async def test_consultation_settings(
    payload: ConsultationTestRequest,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ConsultationTestResponse:
    service = ConsultationConfigService(AppSettingsRepository(db))
    success, message, provider = await service.test_connection(payload.message)
    return ConsultationTestResponse(success=success, message=message, provider=provider)
