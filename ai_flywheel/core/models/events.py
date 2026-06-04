"""Event persistence model — stores published events for replay and audit."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel


class PersistedEvent(BaseModel):
    """A persisted platform event for audit and replay."""

    __tablename__ = "events"

    event_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_module: Mapped[str] = mapped_column(String(100), nullable=False)
    venture_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
