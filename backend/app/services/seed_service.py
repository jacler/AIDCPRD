from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import hash_password
from app.data.default_sku_catalog import DEFAULT_SKU_CATALOG
from app.models.user import UserRole
from app.repositories.sku_repository import SKURepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserCreate


async def seed_admin_user(session: AsyncSession, settings: Settings) -> None:
    repo = UserRepository(session)
    existing = await repo.get_by_email(settings.admin_email)
    if existing is not None:
        return
    await repo.create(
        UserCreate(
            email=settings.admin_email,
            display_name=settings.admin_display_name,
            password=settings.admin_password,
            role=UserRole.ADMIN,
        ),
        hashed_password=hash_password(settings.admin_password),
    )


async def seed_default_skus(session: AsyncSession) -> None:
    """Insert preset SKUs that are not yet in the catalog (idempotent upsert)."""
    repo = SKURepository(session)
    for item in DEFAULT_SKU_CATALOG:
        existing = await repo.find_by_identity(item.category, item.vendor, item.model)
        if existing is None:
            await repo.create(item)
