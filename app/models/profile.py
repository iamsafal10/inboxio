"""Profile model representing user career, resume, and writing style info."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class Profile(Base):
    """User profile model containing background context and writing style."""

    __tablename__ = "profiles"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    resume_text = Column(
        Text,
        nullable=True,
    )
    career_info = Column(
        Text,
        nullable=True,
    )
    writing_style_samples = Column(
        Text,
        nullable=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False,
    )

    # Relationship
    user = relationship("User", back_populates="profile")
