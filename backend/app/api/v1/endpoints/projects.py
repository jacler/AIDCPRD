from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.planner.multi_plan import build_multi_plans
from app.schemas.api import (
    CalculateCostRequest,
    CalculateCostResponse,
    GenerateTopologyRequest,
    GenerateTopologyResponse,
    MultiPlanResponse,
    PlanTradeOffItem,
    ProjectDetailRead,
)
from app.schemas.consultation import UpdateTopologyRequest
from app.schemas.hardware import (
    PaginatedResponse,
    ProjectBOMRead,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=PaginatedResponse)
async def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    repo = ProjectRepository(db)
    items, total = await repo.list_projects(page=page, page_size=page_size)
    return PaginatedResponse(
        items=[ProjectRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(
    payload: ProjectCreate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    repo = ProjectRepository(db)
    project = await repo.create(payload)
    return ProjectRead.model_validate(project)


@router.post("/generate-topology", response_model=GenerateTopologyResponse)
async def generate_topology(
    payload: GenerateTopologyRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateTopologyResponse:
    service = ProjectService(db)
    return await service.generate_topology(payload)


@router.get("/{project_id}", response_model=ProjectDetailRead)
async def get_project(
    project_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectDetailRead:
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")
    base = ProjectRead.model_validate(project)
    return ProjectDetailRead(
        **base.model_dump(),
        bom=[ProjectBOMRead.model_validate(row) for row in project.bom_items],
    )


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")
    updated = await repo.update(project, payload)
    return ProjectRead.model_validate(updated)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")
    await repo.delete(project)


@router.put("/{project_id}/topology", response_model=GenerateTopologyResponse)
async def update_topology(
    project_id: UUID,
    payload: UpdateTopologyRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateTopologyResponse:
    service = ProjectService(db)
    return await service.update_topology_manual(project_id, payload)


@router.get("/{project_id}/multi-plan", response_model=MultiPlanResponse)
async def get_multi_plan(
    project_id: UUID,
    electricity_price: float = Query(default=0.8, ge=0.1, le=5.0, description="电价 元/kWh"),
    pue: float = Query(default=1.3, ge=1.0, le=2.5),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MultiPlanResponse:
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")

    breakdown = project.cost_breakdown_json
    if breakdown and "total" not in breakdown:
        breakdown = {
            **breakdown,
            "total": sum(float(breakdown.get(k, 0)) for k in ("COMPUTE", "NETWORK", "STORAGE", "SOFTWARE", "INFRA")),
        }

    raw_plans = build_multi_plans(
        cost_breakdown=breakdown,
        target_gpus=project.target_gpus,
        topology=project.topology_json,
        scenario=project.scenario.value,
        electricity_price_cny_per_kwh=electricity_price,
        pue=pue,
    )

    return MultiPlanResponse(
        project_id=project_id,
        electricity_price_cny_per_kwh=electricity_price,
        pue=pue,
        plans=[PlanTradeOffItem.model_validate(p) for p in raw_plans],
    )


@router.post("/{project_id}/calculate-cost", response_model=CalculateCostResponse)
async def calculate_cost(
    project_id: UUID,
    payload: CalculateCostRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalculateCostResponse:
    service = ProjectService(db)
    return await service.calculate_cost(
        project_id=project_id,
        bom_inputs=payload.bom_items,
        pricing_rules=payload.pricing_rules,
    )
