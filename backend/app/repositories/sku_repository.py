from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hardware import SKUCatalog, SKUCategory
from app.schemas.hardware import SKUCatalogCreate, SKUCatalogUpdate


class SKURepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _apply_filters(self, query, *, category: SKUCategory | None, search: str | None):
        if category is not None:
            query = query.where(SKUCatalog.category == category)
        if search:
            pattern = f"%{search.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(SKUCatalog.model).like(pattern),
                    func.lower(SKUCatalog.vendor).like(pattern),
                )
            )
        return query

    async def create(self, data: SKUCatalogCreate) -> SKUCatalog:
        sku = SKUCatalog(**data.model_dump())
        self.session.add(sku)
        await self.session.flush()
        await self.session.refresh(sku)
        return sku

    async def create_many(self, items: list[SKUCatalogCreate]) -> list[SKUCatalog]:
        skus = [SKUCatalog(**item.model_dump()) for item in items]
        self.session.add_all(skus)
        await self.session.flush()
        for sku in skus:
            await self.session.refresh(sku)
        return skus

    async def get_by_id(self, sku_id: UUID) -> SKUCatalog | None:
        return await self.session.get(SKUCatalog, sku_id)

    async def get_by_ids(self, sku_ids: list[UUID]) -> list[SKUCatalog]:
        if not sku_ids:
            return []
        result = await self.session.execute(
            select(SKUCatalog).where(SKUCatalog.id.in_(sku_ids))
        )
        return list(result.scalars().all())

    async def list_skus(
        self,
        *,
        category: SKUCategory | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SKUCatalog], int]:
        query = select(SKUCatalog)
        count_query = select(func.count()).select_from(SKUCatalog)

        query = self._apply_filters(query, category=category, search=search)
        count_query = self._apply_filters(count_query, category=category, search=search)

        total = (await self.session.execute(count_query)).scalar_one()
        offset = (page - 1) * page_size
        result = await self.session.execute(
            query.order_by(SKUCatalog.created_at.desc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def find_by_category(self, category: SKUCategory) -> SKUCatalog | None:
        result = await self.session.execute(
            select(SKUCatalog)
            .where(SKUCatalog.category == category)
            .order_by(SKUCatalog.created_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def find_by_identity(
        self, category: SKUCategory, vendor: str, model: str
    ) -> SKUCatalog | None:
        result = await self.session.execute(
            select(SKUCatalog)
            .where(
                SKUCatalog.category == category,
                func.lower(SKUCatalog.vendor) == vendor.strip().lower(),
                func.lower(SKUCatalog.model) == model.strip().lower(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update(self, sku: SKUCatalog, data: SKUCatalogUpdate) -> SKUCatalog:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(sku, field, value)
        await self.session.flush()
        await self.session.refresh(sku)
        return sku

    async def delete(self, sku: SKUCatalog) -> None:
        await self.session.delete(sku)
        await self.session.flush()
