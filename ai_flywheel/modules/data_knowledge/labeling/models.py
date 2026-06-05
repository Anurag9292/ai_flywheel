"""Labeling & Ground Truth — SQLAlchemy models.

LabelingTask: A labeling task definition with instructions and valid labels.
LabelItem: An individual item to be labeled, with multi-annotator support.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class LabelingTask(BaseModel, VentureScopedMixin):
    """A labeling task definition with instructions and valid labels."""

    __tablename__ = "labeling_tasks"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # classification | extraction | rating | comparison | free_text
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    label_options: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )  # valid labels for classification
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="active"
    )  # active | completed | archived
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    labeled_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class LabelItem(BaseModel, VentureScopedMixin):
    """An individual item to be labeled, with multi-annotator support."""

    __tablename__ = "label_items"

    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("labeling_tasks.id"), nullable=False
    )
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    labels: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )  # [{annotator_id, label, confidence, notes}]
    consensus_label: Mapped[str | None] = mapped_column(String, nullable=True)
    is_gold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="pending"
    )  # pending | labeled | disputed | resolved
