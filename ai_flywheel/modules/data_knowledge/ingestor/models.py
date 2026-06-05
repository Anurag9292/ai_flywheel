"""SQLAlchemy models for the Universal Ingestor module.

DataSource — represents an external data source (CSV, JSON, PDF, API, etc.)
IngestionRecord — tracks individual ingestion runs with metrics
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class DataSource(BaseModel, VentureScopedMixin):
    """A configured data source that can be ingested from."""

    __tablename__ = "data_sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # csv, json, pdf, html, api, text
    config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )  # connection details, credentials ref, schedule
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )  # active, paused, error
    last_ingestion_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    ingestion_records: Mapped[list[IngestionRecord]] = relationship(
        "IngestionRecord", back_populates="source", lazy="selectin"
    )


class IngestionRecord(BaseModel, VentureScopedMixin):
    """Tracks a single ingestion run with metrics and status."""

    __tablename__ = "ingestion_records"

    source_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("data_sources.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # pending, processing, completed, failed
    format_detected: Mapped[str | None] = mapped_column(String(50), nullable=True)
    records_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )  # schema_detected, sample_rows

    # Relationships
    source: Mapped[DataSource | None] = relationship(
        "DataSource", back_populates="ingestion_records"
    )
