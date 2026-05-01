from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.conversation import Conversation, Message

router = APIRouter()


@router.get("/")
async def list_conversations(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all conversations."""
    result = await db.execute(
        select(Conversation).order_by(Conversation.updated_at.desc())
    )
    convs = result.scalars().all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "project_id": c.project_id,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in convs
    ]


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get full conversation history with all messages."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    return {
        "id": conv.id,
        "title": conv.title,
        "project_id": conv.project_id,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "agent_name": m.agent_name,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a conversation."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)
    await db.commit()
    return {"deleted": True}
