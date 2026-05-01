from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.deliverable import Deliverable

router = APIRouter()


@router.get("/{deliverable_id}")
async def get_deliverable(
    deliverable_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a deliverable by ID."""
    result = await db.execute(
        select(Deliverable).where(
            Deliverable.id == deliverable_id
        )
    )
    deliverable = result.scalar_one_or_none()
    if not deliverable:
        raise HTTPException(
            status_code=404, detail="Deliverable not found"
        )
    return {
        "id": deliverable.id,
        "project_id": deliverable.project_id,
        "title": deliverable.title,
        "content_markdown": deliverable.content_markdown,
        "created_at": deliverable.created_at.isoformat(),
    }


@router.get("/project/{project_id}")
async def list_project_deliverables(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all deliverables for a project."""
    result = await db.execute(
        select(Deliverable)
        .where(Deliverable.project_id == project_id)
        .order_by(Deliverable.created_at.desc())
    )
    deliverables = result.scalars().all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "created_at": d.created_at.isoformat(),
        }
        for d in deliverables
    ]


@router.get("/{deliverable_id}/download")
async def download_deliverable(
    deliverable_id: str,
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    """Download deliverable as Markdown file."""
    result = await db.execute(
        select(Deliverable).where(
            Deliverable.id == deliverable_id
        )
    )
    deliverable = result.scalar_one_or_none()
    if not deliverable:
        raise HTTPException(
            status_code=404, detail="Deliverable not found"
        )
    filename = (
        deliverable.title.replace(" ", "_").lower() + ".md"
    )
    return PlainTextResponse(
        content=deliverable.content_markdown,
        media_type="text/markdown",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )
