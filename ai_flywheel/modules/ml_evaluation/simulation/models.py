"""Simulation Engine — SQLAlchemy models.

Simulation: A collection of scenarios for testing workflows.
"""

from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class Simulation(BaseModel, VentureScopedMixin):
    """A simulation containing scenarios for workflow testing."""

    __tablename__ = "simulations"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_blueprint_id: Mapped[str | None] = mapped_column(String, nullable=True)
    scenarios: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="draft"
    )  # draft | running | completed | failed
    results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    total_scenarios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_scenarios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_scenarios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_estimate_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
