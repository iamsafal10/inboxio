"""Chunk model representing split text segments for vector embedding."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base

def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)

class Chunk(Base):
    """Text chunks split from emails, carrying metadata for retrieval and citations."""
    __tablename__ = "chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email_id = Column(String(36), ForeignKey("emails_indexed.id", ondelete="CASCADE"), index=True, nullable=False)
    
    # Required metadata fields
    gmail_message_id = Column(String(255), index=True, nullable=False)
    gmail_thread_id = Column(String(255), index=True, nullable=False)
    sender = Column(String(255), index=True, nullable=False)
    subject = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), index=True, nullable=False)
    
    # Chunk specific data
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    
    status = Column(String(50), default="chunked", nullable=False) # "chunked", "embedded"
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Relationships
    email = relationship("EmailIndexed", back_populates="chunks")
