"""Prompt Studio SQLAlchemy models.

PromptTemplate — the main template entity with Jinja2 template text.
PromptVersion — immutable snapshots for version history and rollback.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class PromptTemplate(BaseModel, VentureScopedMixin):
    """A managed prompt template with Jinja2 template text and versioning."""

    __tablename__ = "prompt_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    input_variables: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationship to versions
    versions: Mapped[list[PromptVersion]] = relationship(
        "PromptVersion",
        back_populates="template",
        order_by="PromptVersion.version_number.desc()",
        lazy="selectin",
    )


class PromptVersion(BaseModel, VentureScopedMixin):
    """Immutable snapshot of a prompt template at a specific version."""

    __tablename__ = "prompt_versions"

    template_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("prompt_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    input_variables: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    change_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationship back to template
    template: Mapped[PromptTemplate] = relationship(
        "PromptTemplate",
        back_populates="versions",
    )
