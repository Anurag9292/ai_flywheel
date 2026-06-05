# ruff: noqa: E501
"""SQLAlchemy models for Feature Factory."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class FeatureDefinition(BaseModel, VentureScopedMixin):
    """A single feature transform definition."""

    __tablename__ = "feature_definitions"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_fields: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    transform_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # numeric | categorical | text | temporal | composite
    transform_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    output_dtype: Mapped[str] = mapped_column(
        String(20), nullable=False, default="float"
    )  # float | int | str | bool | list
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class FeatureSet(BaseModel, VentureScopedMixin):
    """A named collection of feature definitions applied together."""

    __tablename__ = "feature_sets"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    feature_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )  # draft | computing | ready | stale
