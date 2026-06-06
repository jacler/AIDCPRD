import enum
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SKUCategory(str, enum.Enum):
    GPU = "GPU"
    CPU = "CPU"
    MEM = "MEM"
    SWITCH = "SWITCH"
    OPTIC = "OPTIC"
    STORAGE = "STORAGE"
    SOFTWARE = "SOFTWARE"
    INFRA = "INFRA"


class ProjectScenario(str, enum.Enum):
    TRAINING = "TRAINING"
    INFERENCE = "INFERENCE"
    MIXED = "MIXED"


class ProjectStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CALCULATING = "CALCULATING"
    COMPLETED = "COMPLETED"


class CostDimension(str, enum.Enum):
    COMPUTE = "COMPUTE"
    NETWORK = "NETWORK"
    STORAGE = "STORAGE"
    SOFTWARE = "SOFTWARE"
    INFRA = "INFRA"


class SKUCatalogBase(BaseModel):
    category: SKUCategory
    vendor: str = Field(..., max_length=128)
    model: str = Field(..., max_length=256)
    specs_json: dict[str, Any] = Field(default_factory=dict)
    base_price: Decimal = Field(..., ge=0)
    channel_price: Decimal | None = Field(default=None, ge=0)
    cost_dimension: CostDimension


class SKUCatalogCreate(SKUCatalogBase):
    pass


class SKUCatalogUpdate(BaseModel):
    category: SKUCategory | None = None
    vendor: str | None = Field(default=None, max_length=128)
    model: str | None = Field(default=None, max_length=256)
    specs_json: dict[str, Any] | None = None
    base_price: Decimal | None = Field(default=None, ge=0)
    channel_price: Decimal | None = Field(default=None, ge=0)
    cost_dimension: CostDimension | None = None


class SKUCatalogRead(SKUCatalogBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class SKUCatalogBatchImport(BaseModel):
    items: list[SKUCatalogCreate]


class ProjectBase(BaseModel):
    name: str = Field(..., max_length=256)
    target_gpus: int = Field(..., gt=0)
    scenario: ProjectScenario
    description: str | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=256)
    target_gpus: int | None = Field(default=None, gt=0)
    scenario: ProjectScenario | None = None
    status: ProjectStatus | None = None
    description: str | None = None
    topology_json: dict[str, Any] | None = None
    cost_breakdown_json: dict[str, Any] | None = None


class ProjectRead(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: ProjectStatus
    topology_json: dict[str, Any] | None = None
    cost_breakdown_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class ProjectBOMBase(BaseModel):
    sku_id: UUID
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    total_price: Decimal = Field(..., ge=0)
    cost_dimension: CostDimension


class ProjectBOMCreate(ProjectBOMBase):
    pass


class ProjectBOMRead(ProjectBOMBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    sku: SKUCatalogRead | None = None
    created_at: datetime


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
