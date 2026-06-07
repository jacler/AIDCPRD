from uuid import UUID
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.service import ComplianceService
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError, ValidationError
from app.export.doc_generator import TechnicalProposalInput, generate_technical_proposal_docx
from app.models.user import User
from app.planner.multi_plan import build_multi_plans
from app.repositories.project_repository import ProjectRepository
from app.schemas.export import VisualizationResponse
from app.visualizer.cabinet_layout import render_cabinet_layout_svg
from app.visualizer.topology_renderer import render_topology_svgs

router = APIRouter(prefix="/export", tags=["Export"])


def _content_disposition_attachment(filename: str) -> str:
    """RFC 5987 attachment header — HTTP headers must be latin-1 safe."""
    ascii_fallback = "".join(
        c if ord(c) < 128 and (c.isalnum() or c in "-_.") else "_" for c in filename
    ).strip("._")
    if not ascii_fallback:
        ascii_fallback = "technical_proposal.docx"
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


def _bom_rows(project) -> list[dict]:
    rows: list[dict] = []
    for item in project.bom_items:
        model = item.sku.model if item.sku else "—"
        category = item.sku.category.value if item.sku else item.cost_dimension.value
        rows.append(
            {
                "category": category,
                "model": model,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "total_price": float(item.total_price),
                "cost_dimension": item.cost_dimension.value,
            }
        )
    return rows


@router.get("/projects/{project_id}/visualizations", response_model=VisualizationResponse)
async def get_project_visualizations(
    project_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VisualizationResponse:
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")
    if not project.topology_json:
        raise ValidationError("项目尚未生成拓扑，请先在设计器中生成拓扑")

    topo = render_topology_svgs(project.topology_json)
    cabinet = render_cabinet_layout_svg(project.topology_json)

    return VisualizationResponse(
        project_id=str(project_id),
        convergence_ratio=topo.convergence_ratio,
        compute_network_svg=topo.compute_svg,
        storage_network_svg=topo.storage_svg,
        cabinet_layout_svg=cabinet.svg,
        cabinet_warnings=cabinet.warnings,
        metadata={**topo.metadata, "total_racks": cabinet.total_racks, "total_power_kw": cabinet.total_power_kw},
    )


@router.get("/projects/{project_id}/technical-proposal")
async def download_technical_proposal(
    project_id: UUID,
    electricity_price: float = 0.8,
    pue: float = 1.3,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")
    if not project.topology_json:
        raise ValidationError("项目尚未生成拓扑，请先在设计器中生成拓扑")

    topo_vis = render_topology_svgs(project.topology_json)
    cabinet = render_cabinet_layout_svg(project.topology_json)

    compliance_stored = (project.topology_json or {}).get("compliance")
    compliance_result = None
    if compliance_stored:
        service = ComplianceService()
        bom_meta = [
            {
                "vendor": row.sku.vendor,
                "model": row.sku.model,
                "category": row.sku.category.value,
            }
            for row in project.bom_items
            if row.sku
        ]
        compliance_result = service.evaluate(
            project_name=project.name,
            target_gpus=project.target_gpus,
            compliance=project.description,
            domestic_mode=compliance_stored.get("domestic_mode", False),
            frameworks=compliance_stored.get("frameworks", ["pytorch"]),
            bom_items=bom_meta,
        )

    plans = build_multi_plans(
        cost_breakdown=project.cost_breakdown_json,
        target_gpus=project.target_gpus,
        topology=project.topology_json,
        scenario=project.scenario.value,
        electricity_price_cny_per_kwh=electricity_price,
        pue=pue,
    )

    consultation_summary: list[str] = []
    diag = (project.topology_json or {}).get("consultation_summary")
    if isinstance(diag, list):
        consultation_summary = [str(x) for x in diag]

    payload = TechnicalProposalInput(
        project_name=project.name,
        target_gpus=project.target_gpus,
        scenario=project.scenario.value,
        description=project.description,
        topology=project.topology_json,
        cost_breakdown=project.cost_breakdown_json,
        bom_items=_bom_rows(project),
        multi_plans=plans,
        compliance_result=compliance_result,
        consultation_summary=consultation_summary,
        topology_compute_svg=topo_vis.compute_svg,
        topology_storage_svg=topo_vis.storage_svg,
        cabinet_svg=cabinet.svg,
        convergence_ratio=topo_vis.convergence_ratio,
    )

    doc_bytes = generate_technical_proposal_docx(payload)
    filename = f"{project.name}_technical_proposal.docx"

    return Response(
        content=doc_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": _content_disposition_attachment(filename)},
    )
