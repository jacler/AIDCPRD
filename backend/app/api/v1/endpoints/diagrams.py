from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError, ValidationError
from app.export.delivery_package import build_delivery_package, generate_delivery_package
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.schemas.diagram import DiagramGenerateRequest, DiagramGenerateResponse, PatternListResponse
from app.schemas.hardware import ProjectUpdate
from app.templates.arch_patterns import auto_select_template, list_patterns, match_pattern
from app.visualizer.aidc_golden_rules import minimal_runnable_template, sanitize_mermaid_for_render
from app.visualizer.diagram_generator import generate_architecture_diagram

router = APIRouter(prefix="/diagrams", tags=["Architecture Diagrams"])


@router.get("/minimal-template")
async def get_minimal_mermaid_template(_: User = Depends(get_current_user)) -> dict:
    """V4.0 最小可运行模板 — 用于 mermaid.live 验证."""
    code = sanitize_mermaid_for_render(minimal_runnable_template())
    return {"mermaid_code": code, "version": "4.0"}


def _to_response(pkg, *, project_id: str | None = None) -> DiagramGenerateResponse:
    mermaid_code = sanitize_mermaid_for_render(pkg.mermaid_code)
    return DiagramGenerateResponse(
        project_id=project_id,
        pattern_id=pkg.pattern_id,
        pattern_name=pkg.pattern_name,
        mermaid_code=mermaid_code,
        param_table=pkg.param_table,
        convergence_ratio=pkg.convergence_ratio,
        design_points=pkg.talking_points,
        talking_points=pkg.talking_points,
        render_tools=pkg.render_tools,
        validation_issues=pkg.validation_issues,
        compliance_notes="",
        data_disclaimer=pkg.compliance_statement,
        compliance_statement=pkg.compliance_statement,
        compliance_checklist=pkg.compliance_checklist,
        model_warnings=pkg.model_warnings,
        figure_caption=pkg.figure_caption,
        speaker_notes="\n".join(pkg.talking_points),
        export_mode=pkg.export_mode,
        export_hints=pkg.export_hints,
        render_guide=pkg.render_guide,
    )


@router.get("/patterns", response_model=PatternListResponse)
async def get_arch_patterns(_: User = Depends(get_current_user)) -> PatternListResponse:
    return PatternListResponse(patterns=list_patterns())


@router.post("/generate", response_model=DiagramGenerateResponse)
async def generate_diagram(
    payload: DiagramGenerateRequest,
    _: User = Depends(get_current_user),
) -> DiagramGenerateResponse:
    pkg = generate_delivery_package(
        requirement=payload.requirement,
        pattern_id=payload.pattern_id,
        target_gpus=payload.target_gpus or 64,
        scenario=payload.scenario or "TRAINING",
        convergence_ratio=payload.convergence_ratio,
        device_overrides=payload.device_overrides or None,
        liquid_cooling=payload.liquid_cooling,
        domestic_mode=payload.domestic_mode,
        export_mode=payload.export_mode,
        figure_no=payload.figure_no,
    )
    return _to_response(pkg)


@router.post("/projects/{project_id}/generate", response_model=DiagramGenerateResponse)
async def generate_project_diagram(
    project_id: UUID,
    payload: DiagramGenerateRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiagramGenerateResponse:
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")
    if not project.topology_json:
        raise ValidationError("项目尚未生成拓扑，请先在设计器中生成拓扑")

    requirement = payload.requirement or project.description or project.name
    result = generate_architecture_diagram(
        requirement=requirement,
        pattern_id=payload.pattern_id,
        topology=project.topology_json,
        target_gpus=payload.target_gpus or project.target_gpus,
        scenario=payload.scenario or project.scenario.value,
        convergence_ratio=payload.convergence_ratio,
        device_overrides=payload.device_overrides or None,
        liquid_cooling=payload.liquid_cooling,
        domestic_mode=payload.domestic_mode,
    )
    pkg = build_delivery_package(result, export_mode=payload.export_mode, figure_no=payload.figure_no)

    topo = dict(project.topology_json)
    topo["architecture_diagram"] = {
        "pattern_id": pkg.pattern_id,
        "mermaid_code": pkg.mermaid_code,
        "param_table": pkg.param_table,
        "export_mode": pkg.export_mode,
        "version": "4.0",
    }
    await repo.update(project, ProjectUpdate(topology_json=topo))

    return _to_response(pkg, project_id=str(project_id))


@router.post("/match")
async def match_arch_pattern(
    payload: DiagramGenerateRequest,
    _: User = Depends(get_current_user),
) -> dict:
    pid = auto_select_template(
        {
            "requirement": payload.requirement,
            "target_gpus": payload.target_gpus or 0,
            "scenario": payload.scenario or "",
        }
    )
    pattern = match_pattern(
        payload.requirement,
        target_gpus=payload.target_gpus or 0,
        scenario=payload.scenario or "",
    )
    return {
        "pattern_id": pid,
        "display_name": pattern.display_name,
        "use_case": pattern.use_case,
    }
