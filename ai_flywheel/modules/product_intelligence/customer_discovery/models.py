"""SQLAlchemy models for Customer Discovery Engine.

Tracks discovery projects, interviews, and assumption validation
across the customer discovery lifecycle.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class DiscoveryProject(BaseModel, VentureScopedMixin):
    """A customer discovery project scoped to a problem space / hypothesis."""

    __tablename__ = "discovery_projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    assumptions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active | completed | paused
    interview_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    interviews: Mapped[list[Interview]] = relationship(
        "Interview", back_populates="project", lazy="selectin"
    )
    assumption_records: Mapped[list[Assumption]] = relationship(
        "Assumption", back_populates="project", lazy="selectin"
    )


class Interview(BaseModel, VentureScopedMixin):
    """A single customer discovery interview with extracted insights."""

    __tablename__ = "discovery_interviews"

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("discovery_projects.id"), nullable=False, index=True
    )
    interviewee_role: Mapped[str] = mapped_column(String(255), nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_insights: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    sentiment: Mapped[str] = mapped_column(String(50), default="neutral", nullable=False)
    recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    project: Mapped[DiscoveryProject] = relationship(
        "DiscoveryProject", back_populates="interviews"
    )


class Assumption(BaseModel, VentureScopedMixin):
    """A testable assumption being validated through discovery interviews."""

    __tablename__ = "discovery_assumptions"

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("discovery_projects.id"), nullable=False, index=True
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="unvalidated", nullable=False
    )  # unvalidated | validated | invalidated | uncertain
    evidence_for: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    evidence_against: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    project: Mapped[DiscoveryProject] = relationship(
        "DiscoveryProject", back_populates="assumption_records"
    )
