"""Apply consultation plan: AI SKU enrichment, project create/update, topology generation."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.hardware import ProjectScenario
from app.repositories.project_repository import ProjectRepository
from app.repositories.sku_repository import SKURepository
from app.schemas.api import GenerateTopologyRequest, GenerateTopologyResponse, NetworkArch
from app.schemas.consultation import ApplyPlanRequest, ApplyPlanResponse, ExtractedRequirements
from app.schemas.hardware import ProjectCreate, ProjectUpdate
from app.services.project_service import ProjectService
from app.services.sku_ai_search import SkuAiSearchService


def _requirement_text(extracted: ExtractedRequirements, fallback: str | None) -> str:
    parts = [
        fallback or "",
        extracted.scheme_summary or "",
        extracted.description or "",
        extracted.industry or "",
    ]
    text = " ".join(p.strip() for p in parts if p and p.strip())
    if not text:
        gpus = extracted.target_gpus or 64
        scenario = extracted.scenario or ProjectScenario.MIXED
        text = f"{gpus} GPU {scenario.value} datacenter cluster"
    return text[:4000]


class PlanApplyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.project_service = ProjectService(session)
        self.sku_search = SkuAiSearchService(SKURepository(session))

    async def apply(
        self,
        request: ApplyPlanRequest,
        *,
        settings: dict | None = None,
    ) -> ApplyPlanResponse:
        extracted = request.extracted
        if not extracted.target_gpus:
            raise ValidationError("方案缺少目标 GPU 数量，请继续与顾问对话完善参数")

        skus_imported = 0
        sku_note = ""
        if request.import_skus:
            requirement = _requirement_text(extracted, request.requirement_text)
            imported, _skipped, sku_note, _raw, _engine = await self.sku_search.suggest_and_import(
                requirement,
                extracted=extracted.model_dump(exclude_none=True),
                settings=settings,
            )
            skus_imported = len(imported)

        scenario = extracted.scenario or ProjectScenario.MIXED
        gpus_per_node = extracted.gpus_per_node or 8
        switch_ports = extracted.switch_ports or 64
        network_arch = NetworkArch.FAT_TREE
        if extracted.network_arch:
            try:
                network_arch = NetworkArch(extracted.network_arch)
            except ValueError:
                pass

        if request.project_id:
            project = await self.projects.get_by_id(request.project_id)
            if project is None:
                raise NotFoundError(f"Project {request.project_id} not found")
            project = await self.projects.update(
                project,
                ProjectUpdate(
                    name=extracted.project_name or project.name,
                    target_gpus=extracted.target_gpus,
                    scenario=scenario,
                    description=extracted.description or project.description,
                ),
            )
        else:
            name = extracted.project_name or f"{extracted.target_gpus}卡{scenario.value}集群"
            project = await self.projects.create(
                ProjectCreate(
                    name=name,
                    target_gpus=extracted.target_gpus,
                    scenario=scenario,
                    description=extracted.description,
                )
            )

        topology_result = await self.project_service.generate_topology(
            GenerateTopologyRequest(
                target_gpus=extracted.target_gpus,
                scenario=scenario,
                network_arch=network_arch,
                gpus_per_node=gpus_per_node,
                switch_ports=switch_ports,
                project_id=project.id,
            )
        )

        message = f"已生成拓扑与初步 BOM（{len(topology_result.bom)} 项）"
        if skus_imported:
            message += f"，新增 SKU {skus_imported} 条"

        return ApplyPlanResponse(
            project_id=project.id,
            project_name=project.name,
            ready_to_generate=True,
            topology=topology_result.topology,
            topology_result=topology_result,
            bom_count=len(topology_result.bom),
            skus_imported=skus_imported,
            sku_search_note=sku_note,
            message=message,
        )
