"""Synthetic Data Generator — SQLAlchemy models.

SyntheticDataset: A generated dataset with schema, method, and quality metadata.
"""

from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class SyntheticDataset(BaseModel, VentureScopedMixin):
    """A synthetic dataset generated from a schema definition."""

    __tablename__ = "synthetic_datasets"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_dataset_name: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    generation_method: Mapped[str] = mapped_column(
        String, nullable=False, default="statistical"
    )  # llm | statistical | augmentation
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    schema_definition: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="generating"
    )  # generating | ready | validated | rejected
