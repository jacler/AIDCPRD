from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.hardware import SKUCategory
from app.repositories.sku_repository import SKURepository
from app.schemas.hardware import (
    PaginatedResponse,
    SKUCatalogBatchImport,
    SKUCatalogCreate,
    SKUCatalogRead,
    SKUCatalogUpdate,
)

router = APIRouter(prefix="/catalog", tags=["SKU Catalog"])


@router.get("/skus", response_model=PaginatedResponse)
async def list_skus(
    category: SKUCategory | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    repo = SKURepository(db)
    items, total = await repo.list_skus(category=category, page=page, page_size=page_size)
    return PaginatedResponse(
        items=[SKUCatalogRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/skus/{sku_id}", response_model=SKUCatalogRead)
async def get_sku(
    sku_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SKUCatalogRead:
    repo = SKURepository(db)
    sku = await repo.get_by_id(sku_id)
    if sku is None:
        raise NotFoundError(f"SKU {sku_id} not found")
    return SKUCatalogRead.model_validate(sku)


@router.post("/skus", response_model=SKUCatalogRead, status_code=201)
async def create_sku(
    payload: SKUCatalogCreate,
    db: AsyncSession = Depends(get_db),
) -> SKUCatalogRead:
    repo = SKURepository(db)
    sku = await repo.create(payload)
    return SKUCatalogRead.model_validate(sku)


@router.post("/skus/batch-import", response_model=list[SKUCatalogRead], status_code=201)
async def batch_import_skus(
    payload: SKUCatalogBatchImport,
    db: AsyncSession = Depends(get_db),
) -> list[SKUCatalogRead]:
    repo = SKURepository(db)
    skus = await repo.create_many(payload.items)
    return [SKUCatalogRead.model_validate(sku) for sku in skus]


@router.put("/skus/{sku_id}", response_model=SKUCatalogRead)
async def update_sku(
    sku_id: UUID,
    payload: SKUCatalogUpdate,
    db: AsyncSession = Depends(get_db),
) -> SKUCatalogRead:
    repo = SKURepository(db)
    sku = await repo.get_by_id(sku_id)
    if sku is None:
        raise NotFoundError(f"SKU {sku_id} not found")
    updated = await repo.update(sku, payload)
    return SKUCatalogRead.model_validate(updated)


@router.delete("/skus/{sku_id}", status_code=204)
async def delete_sku(
    sku_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = SKURepository(db)
    sku = await repo.get_by_id(sku_id)
    if sku is None:
        raise NotFoundError(f"SKU {sku_id} not found")
    await repo.delete(sku)
