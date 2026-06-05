"""SQLAlchemy models for the Policy Engine module."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class Policy(BaseModel, VentureScopedMixin):
    """A governance policy defining rules and enforcement behavior.

    Policy types: safety, compliance, governance, rate_limit, content, cost
    Enforcement levels: block, warn, log
    """

    __tablename__ = "policies"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    policy_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="safety|compliance|governance|rate_limit|content|cost",
    )

    rules: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        comment="List of rule dicts evaluated during policy checks",
    )

    enforcement: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="warn",
        comment="block|warn|log",
    )

    scope: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {"all": True},
        comment="Scope: {modules: [], agents: [], all: bool}",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    violation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )


class PolicyViolation(BaseModel, VentureScopedMixin):
    """A recorded violation of a policy."""

    __tablename__ = "policy_violations"

    policy_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("policies.id"),
        nullable=False,
        index=True,
    )

    agent_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    module_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    action_attempted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    violation_details: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    enforcement_action: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="blocked|warned|logged",
    )

    resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
