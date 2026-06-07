import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import ValidationError
from app.models.user import User
from app.repositories.app_settings_repository import AppSettingsRepository
from app.schemas.consultation import (
    ApplyPlanRequest,
    ApplyPlanResponse,
    ConsultationChatRequest,
    ConsultationChatResponse,
)
from app.services.consultation_config import ConsultationConfigService
from app.services.plan_apply_service import PlanApplyService
from app.services.requirement_consultant import RequirementConsultant

router = APIRouter(prefix="/consultation", tags=["Requirement Consultation"])

_consultant = RequirementConsultant()


def _project_id_str(project_id) -> str | None:
    return str(project_id) if project_id else None


@router.post("/chat", response_model=ConsultationChatResponse)
async def consultation_chat(
    payload: ConsultationChatRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsultationChatResponse:
    config_service = ConsultationConfigService(AppSettingsRepository(db))
    settings = await config_service.get_raw_settings()
    if not settings.get("enabled", True):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="智能需求咨询已在系统设置中禁用",
        )
    try:
        return await _consultant.chat(
            payload.message,
            payload.session_id,
            project_id=_project_id_str(payload.project_id),
            settings=settings,
        )
    except ValidationError:
        raise


@router.post("/chat/stream")
async def consultation_chat_stream(
    payload: ConsultationChatRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config_service = ConsultationConfigService(AppSettingsRepository(db))
    settings = await config_service.get_raw_settings()
    if not settings.get("enabled", True):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="智能需求咨询已在系统设置中禁用",
        )

    async def event_generator():
        async for event in _consultant.chat_stream(
            payload.message,
            payload.session_id,
            project_id=_project_id_str(payload.project_id),
            settings=settings,
        ):
            yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/apply-plan", response_model=ApplyPlanResponse)
async def apply_consultation_plan(
    payload: ApplyPlanRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplyPlanResponse:
    config_service = ConsultationConfigService(AppSettingsRepository(db))
    settings = await config_service.get_raw_settings()
    service = PlanApplyService(db)
    return await service.apply(payload, settings=settings)
