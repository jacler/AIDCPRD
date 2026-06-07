import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import hash_password
import app.models  # noqa: F401 — register all ORM models
from app.main import app
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserCreate

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_ADMIN_EMAIL = "admin@example.com"
TEST_ADMIN_PASSWORD = "admin123"


@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        repo = UserRepository(session)
        await repo.create(
            UserCreate(
                email=TEST_ADMIN_EMAIL,
                display_name="Test Admin",
                password=TEST_ADMIN_PASSWORD,
                role=UserRole.ADMIN,
            ),
            hashed_password=hash_password(TEST_ADMIN_PASSWORD),
        )
        await session.commit()
        yield session

    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def seed_skus(client: AsyncClient, auth_headers: dict):
    payload = {
        "items": [
            {
                "category": "GPU",
                "vendor": "NVIDIA",
                "model": "H800 80G",
                "specs_json": {"tflops": 989, "power_w": 700},
                "base_price": "280000.00",
                "channel_price": "265000.00",
                "cost_dimension": "COMPUTE",
            },
            {
                "category": "SWITCH",
                "vendor": "Mellanox",
                "model": "QM9700 Leaf",
                "specs_json": {"ports": 64, "bandwidth_gbps": 400},
                "base_price": "120000.00",
                "cost_dimension": "NETWORK",
            },
            {
                "category": "SWITCH",
                "vendor": "Mellanox",
                "model": "QM9700 Spine",
                "specs_json": {"ports": 64},
                "base_price": "150000.00",
                "cost_dimension": "NETWORK",
            },
            {
                "category": "OPTIC",
                "vendor": "Mellanox",
                "model": "400G-SR8",
                "specs_json": {},
                "base_price": "800.00",
                "cost_dimension": "NETWORK",
            },
            {
                "category": "STORAGE",
                "vendor": "Huawei",
                "model": "OceanStor",
                "specs_json": {},
                "base_price": "80000.00",
                "cost_dimension": "STORAGE",
            },
            {
                "category": "SOFTWARE",
                "vendor": "AIDC",
                "model": "Basic_Scheduler",
                "specs_json": {},
                "base_price": "120000.00",
                "cost_dimension": "SOFTWARE",
            },
        ]
    }
    response = await client.post("/api/v1/catalog/skus/batch-import", json=payload, headers=auth_headers)
    assert response.status_code == 201
    return response.json()
