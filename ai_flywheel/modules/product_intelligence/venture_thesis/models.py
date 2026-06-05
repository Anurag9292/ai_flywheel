"""SQLAlchemy models for Venture Thesis Engine.

Tracks venture theses, their underlying assumptions, and supporting/contradicting
evidence through the validation lifecycle.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class Thesis(BaseModel, VentureScopedMixin):
    """A venture thesis representing a core business hypothesis to validate."""

    __tablename__ = "venture_theses"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active | validated | invalidated | pivoted
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assumptions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    kill_signals: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    validation_plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    thesis_assumptions: Mapped[list[ThesisAssumption]] = relationship(
        "ThesisAssumption", back_populates="thesis", lazy="selectin"
    )
    evidence_items: Mapped[list[EvidenceItem]] = relationship(
        "EvidenceItem", back_populates="thesis", lazy="selectin"
    )


class ThesisAssumption(BaseModel, VentureScopedMixin):
    """A testable assumption underlying a venture thesis."""

    __tablename__ = "thesis_assumptions"

    thesis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("venture_theses.id"), nullable=False, index=True
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(
        String(20), default="medium", nullable=False
    )  # critical | high | medium | low
    status: Mapped[str] = mapped_column(
        String(20), default="untested", nullable=False
    )  # untested | testing | validated | invalidated
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    evidence: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    validation_method: Mapped[str | None] = mapped_column(String(255), nullable=True)
    experiment_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    thesis: Mapped[Thesis] = relationship(
        "Thesis", back_populates="thesis_assumptions"
    )
    evidence_items: Mapped[list[EvidenceItem]] = relationship(
        "EvidenceItem", back_populates="assumption", lazy="selectin"
    )


class EvidenceItem(BaseModel, VentureScopedMixin):
    """A piece of evidence supporting or contradicting a thesis/assumption."""

    __tablename__ = "thesis_evidence_items"

    thesis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("venture_theses.id"), nullable=False, index=True
    )
    assumption_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("thesis_assumptions.id"), nullable=True, index=True
    )
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # interview | experiment | market_signal | metric | observation
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # supports | contradicts | neutral
    strength: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    thesis: Mapped[Thesis] = relationship(
        "Thesis", back_populates="evidence_items"
    )
    assumption: Mapped[ThesisAssumption | None] = relationship(
        "ThesisAssumption", back_populates="evidence_items"
    )
