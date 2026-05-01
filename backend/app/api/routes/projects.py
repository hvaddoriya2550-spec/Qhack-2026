from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.project import Project
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter()


@router.post("/", response_model=ProjectResponse)
async def create_project(
    data: ProjectCreate, db: AsyncSession = Depends(get_db)
) -> Project:
    project = Project(**data.model_dump(exclude_none=True))
    # Auto-advance past data_gathering if lead data is already complete
    if (
        project.customer_name
        and project.product_interest
        and project.house_type
        and project.heating_type
    ):
        project.status = "research"
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)) -> list[Project]:
    result = await db.execute(select(Project).order_by(Project.updated_at.desc()))
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str, data: ProjectUpdate, db: AsyncSession = Depends(get_db)
) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for key, value in data.model_dump(exclude_none=True).items():
        setattr(project, key, value)

    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{project_id}/conversation")
async def get_project_conversation(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the most recent conversation for a project.

    Returns {conversation_id: str} or 404 if none exists.
    Used by the frontend to resume a project's chat.
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.updated_at.desc())
        .limit(1)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(
            status_code=404,
            detail="No conversation found",
        )
    return {"conversation_id": conv.id}
