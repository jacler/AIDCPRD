from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.hardware import Project, ProjectBOM, ProjectStatus
from app.schemas.hardware import ProjectCreate, ProjectUpdate


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: ProjectCreate) -> Project:
        project = Project(**data.model_dump(), status=ProjectStatus.DRAFT)
        self.session.add(project)
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def get_by_id(self, project_id: UUID) -> Project | None:
        result = await self.session.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.bom_items).selectinload(ProjectBOM.sku))
        )
        return result.scalar_one_or_none()

    async def list_projects(
        self, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Project], int]:
        total = (await self.session.execute(select(func.count()).select_from(Project))).scalar_one()
        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(Project).order_by(Project.updated_at.desc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def update(self, project: Project, data: ProjectUpdate) -> Project:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def delete(self, project: Project) -> None:
        await self.session.delete(project)
        await self.session.flush()

    async def replace_bom(self, project: Project, bom_rows: list[ProjectBOM]) -> Project:
        project.bom_items.clear()
        await self.session.flush()
        project.bom_items.extend(bom_rows)
        await self.session.flush()
        await self.session.refresh(project, attribute_names=["bom_items"])
        return project
