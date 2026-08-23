from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
import uuid

from app.core.database import Base
from app.models.user import get_utc_now

class ColdEmailDraft(Base):
    __tablename__ = "cold_email_drafts"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_context = Column(
        Text,
        nullable=False,
    )
    original_body = Column(
        Text,
        nullable=False,
    )
    flags = Column(
        JSON,
        nullable=True,
    )
    status = Column(
        String(50),
        nullable=False,
        default="DRAFTED",
    )
    created_at = Column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False,
    )
