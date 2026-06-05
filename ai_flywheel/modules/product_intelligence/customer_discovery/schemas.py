"""Pydantic schemas for Customer Discovery Engine.

Request/response models for the service API layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# --- Sub-models ---


class InsightItem(BaseModel):
    """A single insight extracted from an interview transcript."""

    category: str = Field(description="Category: pain_point, need, behavior, motivation, workflow")
    finding: str = Field(description="The key insight in a clear sentence")
    quote: str = Field(description="Direct quote from the transcript supporting this insight")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence level 0-1")


class AssumptionUpdate(BaseModel):
    """How an interview affected an assumption."""

    assumption_index: int = Field(description="Index into the project's assumptions list")
    direction: Literal["supports", "contradicts", "neutral"] = Field(
        description="Whether this evidence supports or contradicts the assumption"
    )
    evidence: str = Field(description="The specific evidence from the interview")


# --- Project ---


class DiscoveryProjectCreate(BaseModel):
    """Request to create a new discovery project."""

    name: str = Field(min_length=1, max_length=255)
    domain: str = Field(min_length=1, max_length=255, description="Problem domain / market")
    hypothesis: str = Field(min_length=10, description="Core hypothesis to validate")
    assumptions: list[str] = Field(
        min_length=1,
        description="Testable assumptions underlying the hypothesis",
    )


class DiscoveryProjectResponse(BaseModel):
    """Response containing discovery project details."""

    id: str
    venture_id: str
    name: str
    domain: str
    hypothesis: str
    assumptions: list[str]
    status: str
    interview_count: int
    confidence_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Interview Guide ---


class InterviewGuideRequest(BaseModel):
    """Request to generate an interview guide."""

    project_id: str
    target_role: str = Field(description="Role of the person being interviewed")
    focus_areas: list[str] = Field(
        default_factory=list,
        description="Specific areas to probe deeper on",
    )


class InterviewGuideResponse(BaseModel):
    """Generated interview guide with questions and scripts."""

    project_id: str
    target_role: str
    questions: list[str] = Field(description="Open-ended interview questions")
    opening_script: str = Field(description="How to open the interview")
    probing_tips: list[str] = Field(description="Tips for follow-up probing")


# --- Transcript Analysis ---


class TranscriptAnalysisRequest(BaseModel):
    """Request to analyze an interview transcript."""

    project_id: str
    interviewee_role: str
    transcript: str = Field(min_length=50, description="Full interview transcript")


class TranscriptAnalysisResponse(BaseModel):
    """Results of analyzing an interview transcript."""

    interview_id: str
    insights: list[InsightItem]
    assumptions_updated: list[AssumptionUpdate]
    sentiment: str = Field(description="Overall sentiment: positive, negative, mixed, neutral")


# --- Synthesis ---


class SynthesisRequest(BaseModel):
    """Request to synthesize findings across all project interviews."""

    project_id: str


class SynthesisResponse(BaseModel):
    """Synthesized findings across all interviews in a project."""

    project_id: str
    patterns: list[str] = Field(description="Recurring patterns observed across interviews")
    key_findings: list[str] = Field(description="Most important validated findings")
    recommendations: list[str] = Field(description="Actionable next steps")
    overall_confidence: float = Field(ge=0.0, le=1.0)
    assumption_status: list[dict] = Field(
        description="Current status of each assumption with evidence summary"
    )
