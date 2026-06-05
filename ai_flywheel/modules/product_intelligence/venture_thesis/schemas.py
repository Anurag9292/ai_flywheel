"""Pydantic schemas for Venture Thesis Engine.

Request/response models for the service API layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# --- Creation schemas ---


class AssumptionCreate(BaseModel):
    """Request to create a thesis assumption."""

    statement: str = Field(min_length=1, description="The testable assumption statement")
    risk_level: Literal["critical", "high", "medium", "low"] = Field(
        default="medium", description="Risk level if this assumption is wrong"
    )
    validation_method: str | None = Field(
        default=None, description="Suggested method for validating this assumption"
    )


class ThesisCreate(BaseModel):
    """Request to create a new venture thesis."""

    title: str = Field(min_length=1, max_length=255, description="Short thesis title")
    hypothesis: str = Field(
        min_length=10,
        description="Structured hypothesis: We believe X because Y, disproven if Z",
    )
    assumptions: list[AssumptionCreate] = Field(
        default_factory=list, description="Underlying assumptions to track"
    )
    kill_signals: list[str] = Field(
        default_factory=list,
        description="Conditions that would invalidate the thesis entirely",
    )


# --- Response schemas ---


class AssumptionResponse(BaseModel):
    """Response containing assumption details."""

    id: str
    thesis_id: str
    statement: str
    risk_level: str
    status: str
    confidence: float
    evidence_count: int
    validation_method: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ThesisResponse(BaseModel):
    """Response containing thesis details with assumptions."""

    id: str
    venture_id: str
    title: str
    hypothesis: str
    status: str
    confidence: float
    evidence_count: int
    assumptions: list[AssumptionResponse]
    kill_signals: list[str]
    validation_plan: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Evidence schemas ---


class AddEvidenceRequest(BaseModel):
    """Request to add evidence to a thesis/assumption."""

    thesis_id: str
    assumption_id: str | None = Field(
        default=None, description="Specific assumption this evidence relates to"
    )
    source_type: Literal["interview", "experiment", "market_signal", "metric", "observation"]
    source_id: str | None = Field(
        default=None, description="External reference ID for the source"
    )
    content: str = Field(min_length=1, description="Description of the evidence")
    direction: Literal["supports", "contradicts", "neutral"]
    strength: float = Field(default=0.5, ge=0.0, le=1.0, description="Evidence strength 0-1")


class EvidenceResponse(BaseModel):
    """Response containing evidence item details."""

    id: str
    thesis_id: str
    assumption_id: str | None
    source_type: str
    source_id: str | None
    content: str
    direction: str
    strength: float
    recorded_at: datetime

    model_config = {"from_attributes": True}


# --- Validation Plan schemas ---


class ValidationStep(BaseModel):
    """A single step in a validation plan."""

    assumption: str = Field(description="The assumption being validated")
    method: str = Field(description="How to validate it")
    success_criteria: str = Field(description="What counts as validation")
    effort: str = Field(description="Estimated effort: low, medium, high")
    priority: int = Field(description="Priority order (1 = highest)")


class ValidationPlanRequest(BaseModel):
    """Request to generate a validation plan for a thesis."""

    thesis_id: str


class ValidationPlanResponse(BaseModel):
    """Generated validation plan with prioritized steps."""

    thesis_id: str
    plan: list[ValidationStep]
    estimated_time: str = Field(description="Overall time estimate")
    estimated_cost: str = Field(description="Overall cost estimate")


# --- Memo schemas ---


class ThesisMemoRequest(BaseModel):
    """Request to generate a venture memo for a thesis."""

    thesis_id: str


class ThesisMemoResponse(BaseModel):
    """Generated venture memo summarizing thesis state."""

    thesis_id: str
    memo: str = Field(description="Full venture memo text")
    confidence_summary: dict = Field(description="Confidence breakdown by assumption")
    next_actions: list[str] = Field(description="Recommended next actions")
