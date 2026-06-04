"""Base SQLAlchemy model with standard audit fields.

All models inherit from Base and get:
- UUID7 primary key (time-sortable)
- created_at, updated_at timestamps
- Soft delete via deleted_at
- Venture scoping mixin for RLS-enabled tables
"""

from __future__ import annotations

from datetime import datetime

import uuid7 as uuid7_lib
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def generate_uuid7() -> str:
    """Generate a UUID7 (time-sortable UUID)."""
    return str(uuid7_lib.uuid7())


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class TimestampMixin:
    """Adds created_at and updated_at to any model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds soft delete capability via deleted_at timestamp."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class VentureScopedMixin:
    """Mixin for models scoped to a venture (RLS-enabled tables)."""

    venture_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )


class BaseModel(Base, TimestampMixin, SoftDeleteMixin):
    """Standard base model with UUID7 PK + audit fields."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid7,
    )
