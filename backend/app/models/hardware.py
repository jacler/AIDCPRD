import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


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


class SKUCatalog(Base):
    __tablename__ = "sku_catalog"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    category: Mapped[SKUCategory] = mapped_column(
        Enum(SKUCategory, name="sku_category", native_enum=False),
        nullable=False,
        index=True,
    )
    vendor: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(256), nullable=False)
    specs_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
    base_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    channel_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    cost_dimension: Mapped[CostDimension] = mapped_column(
        Enum(CostDimension, name="cost_dimension", native_enum=False),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    bom_items: Mapped[list["ProjectBOM"]] = relationship(
        "ProjectBOM", back_populates="sku"
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    target_gpus: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario: Mapped[ProjectScenario] = mapped_column(
        Enum(ProjectScenario, name="project_scenario", native_enum=False),
        nullable=False,
    )
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status", native_enum=False),
        nullable=False,
        default=ProjectStatus.DRAFT,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    topology_json: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    cost_breakdown_json: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    bom_items: Mapped[list["ProjectBOM"]] = relationship(
        "ProjectBOM", back_populates="project", cascade="all, delete-orphan"
    )


class ProjectBOM(Base):
    __tablename__ = "project_bom"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sku_catalog.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    cost_dimension: Mapped[CostDimension] = mapped_column(
        Enum(CostDimension, name="bom_cost_dimension", native_enum=False),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship("Project", back_populates="bom_items")
    sku: Mapped["SKUCatalog"] = relationship("SKUCatalog", back_populates="bom_items")
