from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.core.database import Base
from app.models.user import get_utc_now

class EmailSendLog(Base):
    __tablename__ = "email_sends_log"

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
    recipient = Column(
        String(255),
        nullable=False,
    )
    draft_reference = Column(
        Text,
        nullable=False,
    )
    status = Column(
        String(50),
        nullable=False,
    )
    error_message = Column(
        Text,
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False,
    )
