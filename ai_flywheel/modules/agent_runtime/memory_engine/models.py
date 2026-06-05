"""SQLAlchemy models for the Memory Engine module."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class MemoryEntry(BaseModel, VentureScopedMixin):
    """A single memory entry across any of the four memory tiers.

    Tiers:
        - working: ephemeral task context for current execution
        - episodic: timestamped past interactions and outcomes
        - semantic: persistent factual knowledge
        - procedural: reusable learned how-to sequences
    """

    __tablename__ = "memory_entries"

    agent_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    memory_tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    importance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
    )

    access_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
    )

    embedding_vector: Mapped[list[float] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
