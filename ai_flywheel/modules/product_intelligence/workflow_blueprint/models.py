"""SQLAlchemy models for Workflow Blueprint Engine.

Tracks workflow blueprints as directed graphs of AI agent, human, tool,
and decision nodes with edges representing control flow.
WorkflowNode is stored as JSONB within the blueprint (not a separate table).
"""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class WorkflowBlueprint(BaseModel, VentureScopedMixin):
    """A workflow blueprint describing an AI-human process as a directed graph."""

    __tablename__ = "workflow_blueprints"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False
    )  # draft | active | archived
    nodes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    edges: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    sla_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fallback_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
