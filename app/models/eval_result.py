"""Evaluation result model for comparing baseline vs agent responses."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, DateTime

from app.core.database import Base


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class EvalResult(Base):
    """Benchmark test results comparing baseline and agent answers on the same row."""

    __tablename__ = "eval_results"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    question_id = Column(
        String(255),
        index=True,
        nullable=False,
    )
    question_text = Column(
        Text,
        nullable=False,
    )
    question_type = Column(
        String(100),
        nullable=False,
    )
    expected_answer_notes = Column(
        Text,
        nullable=True,
    )
    baseline_answer = Column(
        Text,
        nullable=True,
    )
    agent_answer = Column(
        Text,
        nullable=True,
    )
    baseline_score = Column(
        Float,
        nullable=True,
    )
    agent_score = Column(
        Float,
        nullable=True,
    )
    provider = Column(
        String(50),
        nullable=True,
    )
    run_at = Column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False,
    )
