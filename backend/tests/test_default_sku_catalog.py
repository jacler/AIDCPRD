import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.default_sku_catalog import BOM_REQUIRED_MODELS, DEFAULT_SKU_CATALOG
from app.repositories.sku_repository import SKURepository
from app.services.seed_service import seed_default_skus


def test_default_catalog_size_and_bom_models():
    assert len(DEFAULT_SKU_CATALOG) >= 50
    categories = {item.category.value for item in DEFAULT_SKU_CATALOG}
    assert {"GPU", "SWITCH", "OPTIC", "STORAGE", "SOFTWARE", "CPU", "MEM", "INFRA"}.issubset(
        categories
    )
    catalog_keys = {(i.category.value, i.vendor, i.model) for i in DEFAULT_SKU_CATALOG}
    assert BOM_REQUIRED_MODELS.issubset(catalog_keys)


@pytest.mark.asyncio
async def test_seed_default_skus_is_idempotent(db_session: AsyncSession):
    await seed_default_skus(db_session)
    await db_session.commit()
    repo = SKURepository(db_session)
    _items, first_count = await repo.list_skus(page=1, page_size=200)

    await seed_default_skus(db_session)
    await db_session.commit()
    _items2, second_count = await repo.list_skus(page=1, page_size=200)

    assert first_count == second_count
    assert first_count >= len(DEFAULT_SKU_CATALOG)

    for category, vendor, model in BOM_REQUIRED_MODELS:
        from app.models.hardware import SKUCategory

        found = await repo.find_by_identity(SKUCategory(category), vendor, model)
        assert found is not None, f"missing BOM SKU: {vendor} {model}"
