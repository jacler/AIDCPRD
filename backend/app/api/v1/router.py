from fastapi import APIRouter

from app.api.v1.endpoints import auth, catalog, consultation, projects, settings

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(consultation.router)
api_router.include_router(projects.router)
api_router.include_router(settings.router)
