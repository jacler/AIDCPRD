from fastapi import APIRouter

from app.api.v1.endpoints import catalog, projects

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(catalog.router)
api_router.include_router(projects.router)
