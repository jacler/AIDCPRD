from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.schemas.auth import UserCreate, UserUpdate


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: UserCreate, *, hashed_password: str) -> User:
        user = User(
            email=data.email.lower(),
            display_name=data.display_name,
            hashed_password=hashed_password,
            role=data.role,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def list_users(self, *, page: int = 1, page_size: int = 20) -> tuple[list[User], int]:
        count_query = select(func.count()).select_from(User)
        total = (await self.session.execute(count_query)).scalar_one()
        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def update(self, user: User, data: UserUpdate) -> User:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_password(self, user: User, hashed_password: str) -> User:
        user.hashed_password = hashed_password
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def count_admins(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
        )
        return result.scalar_one()
