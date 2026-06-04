"""Venture model — top-level namespace for all AI ventures."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel


class Venture(BaseModel):
    """A venture is a namespace for a specific AI-native startup.

    This table does NOT have RLS — it's a global table.
    """

    __tablename__ = "ventures"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    domain: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    metrics_summary: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, server_default="{}"
    )
