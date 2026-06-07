from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.service import ComplianceService
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.schemas.compliance import ComplianceEvaluateRequest, ComplianceEvaluateResponse
from app.schemas.hardware import ProjectUpdate

router = APIRouter(prefix="/compliance", tags=["Compliance"])


def _bom_from_project(project) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for row in project.bom_items:
        if row.sku:
            items.append(
                {
                    "vendor": row.sku.vendor,
                    "model": row.sku.model,
                    "category": row.sku.category.value,
                }
            )
    return items


def _compliance_from_description(description: str | None) -> str | None:
    if not description:
        return None
    for kw in ("等保三级", "等保3", "等保二级", "信创", "国产化"):
        if kw in description:
            return description
    return None


@router.post("/projects/{project_id}/evaluate", response_model=ComplianceEvaluateResponse)
async def evaluate_project_compliance(
    project_id: UUID,
    payload: ComplianceEvaluateRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComplianceEvaluateResponse:
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")

    compliance = payload.compliance or _compliance_from_description(project.description)
    service = ComplianceService()
    result = service.evaluate(
        project_name=project.name,
        target_gpus=project.target_gpus,
        compliance=compliance,
        industry=payload.industry,
        domestic_mode=payload.domestic_mode,
        frameworks=payload.frameworks,
        bom_items=_bom_from_project(project),
        cross_domain=payload.cross_domain,
        network_zoned=payload.network_zoned,
        audit_logging_enabled=payload.audit_logging_enabled,
    )

    topology = project.topology_json or {}
    topology["compliance"] = {
        "overall_status": result["overall_status"],
        "domestic_mode": payload.domestic_mode,
        "frameworks": payload.frameworks,
        "checklist": result["security_checklist"],
        "audit_trail": result["audit_trail"],
    }
    await repo.update(project, ProjectUpdate(topology_json=topology))

    return ComplianceEvaluateResponse(project_id=str(project_id), **result)


@router.get("/projects/{project_id}/appendix")
async def get_compliance_appendix(
    project_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")

    stored = (project.topology_json or {}).get("compliance")
    if stored and stored.get("audit_trail"):
        service = ComplianceService()
        result = service.evaluate(
            project_name=project.name,
            target_gpus=project.target_gpus,
            compliance=_compliance_from_description(project.description),
            domestic_mode=stored.get("domestic_mode", False),
            frameworks=stored.get("frameworks", ["pytorch"]),
            bom_items=_bom_from_project(project),
        )
        markdown = result["appendix_markdown"]
    else:
        markdown = (
            f"## 合规判定依据附录 — {project.name}\n\n"
            "尚未执行合规评估。请先调用 POST /compliance/projects/{id}/evaluate。"
        )

    return Response(content=markdown, media_type="text/markdown; charset=utf-8")
