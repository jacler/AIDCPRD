from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, Base, engine
from app.api.v1.router import api_router
from app.services.seed_service import seed_admin_user, seed_default_skus
from app.repositories.app_settings_repository import AppSettingsRepository
from app.services.consultation_config import seed_consultation_settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    settings = get_settings()
    async with AsyncSessionLocal() as session:
        await seed_admin_user(session, settings)
        await seed_default_skus(session)
        await seed_consultation_settings(AppSettingsRepository(session))
        await session.commit()

    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="智算数据中心基础设施设计与成本拆解引擎",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get("/", tags=["Health"])
    async def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "message": "API 运行中。请访问前端 http://localhost:3000",
            "docs": "/docs",
            "health": "/health",
            "api": "/api/v1",
        }

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
