"""Pydantic schemas for the Policy Engine module."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PolicyCreate(BaseModel):
    """Request to create a new governance policy."""

    name: str
    description: str = ""
    policy_type: str
    rules: list[dict[str, Any]]
    enforcement: str = "warn"
    scope: dict[str, Any] = Field(default_factory=lambda: {"all": True})


class PolicyUpdate(BaseModel):
    """Request to update an existing policy. All fields optional."""

    name: str | None = None
    description: str | None = None
    rules: list[dict[str, Any]] | None = None
    enforcement: str | None = None
    scope: dict[str, Any] | None = None
    is_active: bool | None = None


class PolicyResponse(BaseModel):
    """Response representing a policy."""

    id: str
    venture_id: str
    name: str
    description: str | None
    policy_type: str
    rules: list[dict[str, Any]]
    enforcement: str
    scope: dict[str, Any]
    is_active: bool
    violation_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PolicyCheckRequest(BaseModel):
    """Request to check an action against all applicable policies."""

    module_name: str
    agent_id: str | None = None
    action: str
    context: dict[str, Any] = Field(default_factory=dict)


class ViolationDetail(BaseModel):
    """Detail about a single policy violation found during a check."""

    policy_id: str
    policy_name: str
    rule_violated: str
    enforcement: str
    message: str


class PolicyCheckResult(BaseModel):
    """Result of a policy check against an action."""

    allowed: bool
    violations: list[ViolationDetail]
    warnings: list[str]


class ViolationResponse(BaseModel):
    """Response representing a recorded policy violation."""

    id: str
    venture_id: str
    policy_id: str
    agent_id: str | None
    module_name: str
    action_attempted: str
    violation_details: dict[str, Any]
    enforcement_action: str
    resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}
