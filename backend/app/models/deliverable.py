import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text

from app.db.base import Base


class Deliverable(Base):
    __tablename__ = "deliverables"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    project_id = Column(
        String, ForeignKey("projects.id"), nullable=False
    )
    title = Column(String(255), default="Sales Pitch Deck")
    content_markdown = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
