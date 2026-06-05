"""Offer Design Engine — SQLAlchemy models.

Module #28: AI-powered offer design including ICP profiling, positioning,
pricing strategy, and conversion-optimized messaging.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class Offer(BaseModel, VentureScopedMixin):
    """A structured offer with ICP, positioning, pricing, and messaging."""

    __tablename__ = "offers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        comment="draft|active|testing|archived",
    )
    icp: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Target profile: behavioral, firmographic, psychographic",
    )
    positioning: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Statement, category, unique value proposition",
    )
    pricing: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Model, tiers, price points",
    )
    messaging: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Headlines, benefits, CTAs",
    )
    objection_rebuttals: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of objection/rebuttal pairs",
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class MessagingVariant(BaseModel, VentureScopedMixin):
    """A/B messaging variant linked to an offer for conversion testing."""

    __tablename__ = "offer_messaging_variants"

    offer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("offers.id"),
        nullable=False,
        index=True,
    )
    variant_name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_persona: Mapped[str] = mapped_column(String(255), nullable=False)
    headline: Mapped[str] = mapped_column(String(500), nullable=False)
    subheadline: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    body_copy: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cta: Mapped[str] = mapped_column(String(255), nullable=False)
    conversion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_control: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
