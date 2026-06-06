import math
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.hardware import (
    CostDimension,
    Project,
    ProjectBOM,
    ProjectScenario,
    ProjectStatus,
    SKUCatalog,
    SKUCategory,
)
from app.repositories.project_repository import ProjectRepository
from app.repositories.sku_repository import SKURepository
from app.schemas.api import (
    BOMItemInput,
    CalculateCostResponse,
    CostBreakdownResponse,
    GenerateTopologyRequest,
    GenerateTopologyResponse,
    PreliminaryBOMItem,
    StoragePlane,
    TopologyCompute,
    TopologyNetwork,
)
from app.schemas.hardware import ProjectBOMRead, ProjectUpdate
from app.services.cost_engine import calculate_5d_cost
from app.services.topology_engine import generate_fat_tree_topology


def _estimate_storage_nodes(servers: int, scenario: ProjectScenario) -> int:
    if scenario == ProjectScenario.TRAINING:
        return max(4, math.ceil(servers / 8))
    if scenario == ProjectScenario.INFERENCE:
        return max(2, math.ceil(servers / 16))
    return max(3, math.ceil(servers / 12))


def _unit_price(sku: SKUCatalog) -> Decimal:
    return sku.channel_price if sku.channel_price is not None else sku.base_price


def _sku_to_dict(sku: SKUCatalog) -> dict[str, Any]:
    return {
        "category": sku.category.value,
        "model": sku.model,
        "cost_dimension": sku.cost_dimension.value,
        "base_price": sku.base_price,
        "channel_price": sku.channel_price,
    }


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.skus = SKURepository(session)

    async def generate_topology(
        self, request: GenerateTopologyRequest
    ) -> GenerateTopologyResponse:
        if request.network_arch.value != "FAT_TREE":
            raise ValidationError(f"Unsupported network architecture: {request.network_arch}")

        topology = generate_fat_tree_topology(
            target_gpus=request.target_gpus,
            gpus_per_node=request.gpus_per_node,
            switch_ports=request.switch_ports,
        )

        storage_nodes = _estimate_storage_nodes(
            topology["compute"]["servers"], request.scenario
        )
        storage = StoragePlane(nodes=storage_nodes)

        bom = await self._build_preliminary_bom(topology, storage_nodes)

        if request.project_id:
            project = await self.projects.get_by_id(request.project_id)
            if project is None:
                raise NotFoundError(f"Project {request.project_id} not found")
            await self.projects.update(
                project,
                ProjectUpdate(
                    topology_json={**topology, "storage": storage.model_dump()},
                    status=ProjectStatus.CALCULATING,
                ),
            )

        return GenerateTopologyResponse(
            compute=TopologyCompute(**topology["compute"]),
            network=TopologyNetwork(**topology["network"]),
            storage=storage,
            bom=bom,
            topology={**topology, "storage": storage.model_dump()},
        )

    async def _build_preliminary_bom(
        self, topology: dict[str, Any], storage_nodes: int
    ) -> list[PreliminaryBOMItem]:
        compute = topology["compute"]
        network = topology["network"]

        bom_specs: list[tuple[SKUCategory, int, str]] = [
            (SKUCategory.GPU, compute["gpus"], "GPU compute"),
            (SKUCategory.SWITCH, network["leaf_switches"], "Leaf switch"),
            (SKUCategory.SWITCH, network["spine_switches"], "Spine switch"),
            (SKUCategory.OPTIC, network["optics_400g"], "400G optic"),
            (SKUCategory.STORAGE, storage_nodes, "Storage node"),
            (SKUCategory.SOFTWARE, 1, "Basic_Scheduler"),
        ]

        items: list[PreliminaryBOMItem] = []
        for category, quantity, label in bom_specs:
            sku = await self.skus.find_by_category(category)
            if category == SKUCategory.SOFTWARE:
                result = await self.session.execute(
                    select(SKUCatalog)
                    .where(
                        SKUCatalog.category == category,
                        SKUCatalog.model == "Basic_Scheduler",
                    )
                    .limit(1)
                )
                sku = result.scalar_one_or_none() or sku

            unit = _unit_price(sku) if sku else Decimal("0")
            items.append(
                PreliminaryBOMItem(
                    sku_id=sku.id if sku else None,
                    category=category.value,
                    model=sku.model if sku else label,
                    quantity=quantity,
                    unit_price=unit,
                    total_price=unit * quantity,
                    cost_dimension=sku.cost_dimension if sku else self._default_dimension(category),
                )
            )
        return items

    @staticmethod
    def _default_dimension(category: SKUCategory) -> CostDimension:
        mapping = {
            SKUCategory.GPU: CostDimension.COMPUTE,
            SKUCategory.SWITCH: CostDimension.NETWORK,
            SKUCategory.OPTIC: CostDimension.NETWORK,
            SKUCategory.STORAGE: CostDimension.STORAGE,
            SKUCategory.SOFTWARE: CostDimension.SOFTWARE,
        }
        return mapping.get(category, CostDimension.INFRA)

    async def calculate_cost(
        self,
        project_id: UUID,
        bom_inputs: list[BOMItemInput],
        pricing_rules: dict[str, Any] | None = None,
    ) -> CalculateCostResponse:
        project = await self.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found")

        sku_ids = [item.sku_id for item in bom_inputs]
        skus = await self.skus.get_by_ids(sku_ids)
        sku_map = {sku.id: sku for sku in skus}

        missing = set(sku_ids) - set(sku_map.keys())
        if missing:
            raise NotFoundError(f"SKU not found: {missing.pop()}")

        engine_items: list[dict[str, Any]] = []
        bom_rows: list[ProjectBOM] = []

        for item in bom_inputs:
            sku = sku_map[item.sku_id]
            unit = _unit_price(sku)
            total = unit * item.quantity
            engine_items.append({"sku": _sku_to_dict(sku), "quantity": item.quantity})
            bom_rows.append(
                ProjectBOM(
                    project_id=project_id,
                    sku_id=sku.id,
                    quantity=item.quantity,
                    unit_price=unit,
                    total_price=total,
                    cost_dimension=sku.cost_dimension,
                )
            )

        breakdown = calculate_5d_cost(engine_items, pricing_rules)
        total = sum(breakdown.values())

        await self.projects.replace_bom(project, bom_rows)
        await self.projects.update(
            project,
            ProjectUpdate(
                cost_breakdown_json=breakdown,
                status=ProjectStatus.COMPLETED,
            ),
        )

        refreshed = await self.projects.get_by_id(project_id)
        assert refreshed is not None

        return CalculateCostResponse(
            project_id=project_id,
            cost_breakdown=CostBreakdownResponse(**breakdown, total=total),
            bom=[ProjectBOMRead.model_validate(row) for row in refreshed.bom_items],
        )
