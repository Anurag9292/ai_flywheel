"""SQLAlchemy models for Product Experience Engine.

Tracks product specifications including personas, features, AI interaction
patterns, screen architecture, and UX flows.
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class ProductSpec(BaseModel, VentureScopedMixin):
    """A product specification with AI-native experience design artifacts."""

    __tablename__ = "product_specs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    personas: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    features: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    ai_interaction_patterns: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    screen_architecture: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ux_flows: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False
    )  # draft | active | archived
