"""Email metadata tracking model."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class EmailIndexed(Base):
    """Metadata tracking for emails indexed and embedded in vector storage."""

    __tablename__ = "emails_indexed"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    gmail_message_id = Column(
        String(255),
        index=True,
        nullable=False,
    )
    gmail_thread_id = Column(
        String(255),
        index=True,
        nullable=False,
    )
    sender = Column(
        String(255),
        index=True,
        nullable=False,
    )
    recipient = Column(
        String(255),
        nullable=False,
    )
    subject = Column(
        Text,
        nullable=True,
    )
    sent_at = Column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )
    chroma_chunk_ids = Column(
        Text,
        nullable=True,
    )
    status = Column(
        String(50),
        default="fetched",
        nullable=False,
    )
    embedded = Column(
        Boolean,
        default=False,
        nullable=False,
    )
    indexed_at = Column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False,
    )

    # Relationship
    user = relationship("User", back_populates="emails")
