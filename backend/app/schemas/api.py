import enum
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.hardware import (
    CostDimension,
    ProjectBOMRead,
    ProjectRead,
    ProjectScenario,
    SKUCatalogRead,
)


class NetworkArch(str, enum.Enum):
    FAT_TREE = "FAT_TREE"


class StoragePlane(BaseModel):
    nodes: int


class TopologyCompute(BaseModel):
    servers: int
    gpus: int


class TopologyNetwork(BaseModel):
    leaf_switches: int
    spine_switches: int
    rdma_nics: int
    dac_cables: int
    optics_400g: int


class PreliminaryBOMItem(BaseModel):
    sku_id: UUID | None = None
    category: str
    model: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    cost_dimension: CostDimension


class GenerateTopologyRequest(BaseModel):
    target_gpus: int = Field(..., gt=0)
    scenario: ProjectScenario
    network_arch: NetworkArch = NetworkArch.FAT_TREE
    gpus_per_node: int = Field(default=8, gt=0)
    switch_ports: int = Field(default=64, ge=2)
    project_id: UUID | None = None


class GenerateTopologyResponse(BaseModel):
    compute: TopologyCompute
    network: TopologyNetwork
    storage: StoragePlane
    bom: list[PreliminaryBOMItem]
    topology: dict[str, Any]


class BOMItemInput(BaseModel):
    sku_id: UUID
    quantity: int = Field(..., gt=0)


class CalculateCostRequest(BaseModel):
    bom_items: list[BOMItemInput]
    pricing_rules: dict[str, Any] = Field(default_factory=dict)
    price_table_id: UUID | None = None


class CostBreakdownResponse(BaseModel):
    COMPUTE: float
    NETWORK: float
    STORAGE: float
    SOFTWARE: float
    INFRA: float
    total: float


class CalculateCostResponse(BaseModel):
    project_id: UUID
    cost_breakdown: CostBreakdownResponse
    bom: list[ProjectBOMRead]


class ProjectDetailRead(ProjectRead):
    bom: list[ProjectBOMRead] = Field(default_factory=list)


class PlanTradeOffItem(BaseModel):
    plan_id: str
    headline: str
    trade_offs: list[str] = Field(default_factory=list)
    failure_boundary: str
    tco_sensitivity: dict[str, Any] = Field(default_factory=dict)
    convergence_ratio: str
    network_technology: str
    mfu_relative: float
    cost_breakdown: dict[str, float] = Field(default_factory=dict)
    hardware_capex: float
    tco_5y: float
    tco_breakdown: dict[str, float] = Field(default_factory=dict)
    recommended: bool = False


class MultiPlanResponse(BaseModel):
    project_id: UUID
    electricity_price_cny_per_kwh: float
    pue: float
    plans: list[PlanTradeOffItem]
