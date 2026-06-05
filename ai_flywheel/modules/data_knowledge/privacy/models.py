"""Privacy & PII Engine — SQLAlchemy models.

PIIDetection: Record of a PII scan and its results.
RetentionPolicy: Data retention rules per category.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class PIIDetection(BaseModel, VentureScopedMixin):
    """Record of a PII scan and its detections."""

    __tablename__ = "pii_detections"

    source_module: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    detections: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )  # [{type, value, start, end, confidence}]
    action_taken: Mapped[str] = mapped_column(
        String, nullable=False, default="none"
    )  # redacted | masked | logged | none
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class RetentionPolicy(BaseModel, VentureScopedMixin):
    """Data retention policy per category."""

    __tablename__ = "retention_policies"

    name: Mapped[str] = mapped_column(String, nullable=False)
    data_category: Mapped[str] = mapped_column(
        String, nullable=False
    )  # personal | financial | health | general
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    action_on_expiry: Mapped[str] = mapped_column(
        String, nullable=False, default="anonymize"
    )  # delete | anonymize | archive
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
