"""User model representing application users and Gmail OAuth credentials."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, LargeBinary
from sqlalchemy.orm import relationship

from app.core.database import Base


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class User(Base):
    """User account model tracking credentials and Gmail OAuth integration."""

    __tablename__ = "users"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    email = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password = Column(
        String(255),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False,
    )

    # Gmail OAuth fields (read and send scopes tracked separately)
    gmail_access_token = Column(
        LargeBinary,
        nullable=True,
    )
    gmail_refresh_token = Column(
        LargeBinary,
        nullable=True,
    )
    gmail_token_expiry = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    gmail_connected = Column(
        Boolean,
        default=False,
        nullable=False,
    )
    gmail_send_scope_granted = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    emails = relationship("EmailIndexed", back_populates="user", cascade="all, delete-orphan")
    memory_facts = relationship("MemoryFact", back_populates="user", cascade="all, delete-orphan")
