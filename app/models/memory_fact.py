"""Memory fact model supporting soft deletion for auditing."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class MemoryFact(Base):
    """User facts extracted by agent with soft-delete support for auditability."""

    __tablename__ = "memory_facts"

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
    fact_text = Column(
        Text,
        nullable=False,
    )
    fact_type = Column(
        String(50),
        nullable=True,
    )
    source = Column(
        String(255),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False,
    )
    active = Column(
        Boolean,
        default=True,
        nullable=False,
    )
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationship
    user = relationship("User", back_populates="memory_facts")
