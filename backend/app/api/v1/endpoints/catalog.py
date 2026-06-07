from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.models.hardware import SKUCategory
from app.models.user import User
from app.repositories.sku_repository import SKURepository
from app.schemas.hardware import (
    PaginatedResponse,
    SKUCatalogBatchImport,
    SKUCatalogCreate,
    SKUCatalogRead,
    SKUCatalogUpdate,
    SkuAiSuggestRequest,
    SkuAiSuggestResponse,
)
from app.repositories.app_settings_repository import AppSettingsRepository
from app.services.consultation_config import ConsultationConfigService
from app.services.sku_ai_search import SkuAiSearchService

router = APIRouter(prefix="/catalog", tags=["SKU Catalog"])


@router.get("/categories")
async def list_categories(_: User = Depends(get_current_user)) -> list[dict[str, str]]:
    labels = {
        "GPU": "GPU",
        "CPU": "CPU",
        "MEM": "内存",
        "SWITCH": "交换机",
        "OPTIC": "光模块",
        "STORAGE": "存储",
        "SOFTWARE": "软件",
        "INFRA": "基建",
    }
    return [{"value": c.value, "label": labels.get(c.value, c.value)} for c in SKUCategory]


@router.get("/skus", response_model=PaginatedResponse)
async def list_skus(
    category: SKUCategory | None = None,
    search: str | None = Query(default=None, max_length=128),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    repo = SKURepository(db)
    items, total = await repo.list_skus(
        category=category, search=search, page=page, page_size=page_size
    )
    return PaginatedResponse(
        items=[SKUCatalogRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/skus/{sku_id}", response_model=SKUCatalogRead)
async def get_sku(
    sku_id: UUID,
    _: User = Depends(get_current_user),
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
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SKUCatalogRead:
    repo = SKURepository(db)
    sku = await repo.create(payload)
    return SKUCatalogRead.model_validate(sku)


@router.post("/skus/batch-import", response_model=list[SKUCatalogRead], status_code=201)
async def batch_import_skus(
    payload: SKUCatalogBatchImport,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SKUCatalogRead]:
    repo = SKURepository(db)
    skus = await repo.create_many(payload.items)
    return [SKUCatalogRead.model_validate(sku) for sku in skus]


@router.put("/skus/{sku_id}", response_model=SKUCatalogRead)
async def update_sku(
    sku_id: UUID,
    payload: SKUCatalogUpdate,
    _: User = Depends(get_current_user),
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
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = SKURepository(db)
    sku = await repo.get_by_id(sku_id)
    if sku is None:
        raise NotFoundError(f"SKU {sku_id} not found")
    await repo.delete(sku)


@router.post("/skus/ai-suggest", response_model=SkuAiSuggestResponse)
async def ai_suggest_skus(
    payload: SkuAiSuggestRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkuAiSuggestResponse:
    config_service = ConsultationConfigService(AppSettingsRepository(db))
    settings = await config_service.get_raw_settings()
    service = SkuAiSearchService(SKURepository(db))

    imported: list[SKUCatalogRead] = []
    skipped: list[SKUCatalogRead] = []
    if payload.import_to_catalog:
        imported, skipped, note, raw_items, engine = await service.suggest_and_import(
            payload.requirement,
            extracted=payload.extracted,
            settings=settings,
        )
    else:
        raw_items, note, engine = await service.suggest(
            payload.requirement,
            extracted=payload.extracted,
            settings=settings,
        )

    items = [
        {
            "category": str(r.get("category", "")),
            "vendor": str(r.get("vendor", "")),
            "model": str(r.get("model", "")),
            "specs_json": r.get("specs_json") or {},
            "base_price": str(r.get("base_price", "0")),
            "channel_price": str(r["channel_price"]) if r.get("channel_price") else None,
            "cost_dimension": str(r.get("cost_dimension", "INFRA")),
            "rationale": str(r.get("rationale", "")),
        }
        for r in raw_items
    ]

    return SkuAiSuggestResponse(
        items=[SkuAiSuggestItem.model_validate(i) for i in items],
        imported=imported,
        skipped=skipped,
        note=note,
        engine=engine,
    )
