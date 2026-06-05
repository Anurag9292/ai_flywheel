"""Offer Design Engine — Pydantic schemas.

Request/response models for offer creation, ICP profiling, positioning,
pricing strategy, and landing page copy generation.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ------------------------------------------------------------------
# Offer CRUD
# ------------------------------------------------------------------


class OfferCreate(BaseModel):
    """Request to create a new offer."""

    name: str
    domain: str
    target_audience: str
    problem_statement: str
    solution_description: str


class OfferResponse(BaseModel):
    """Full offer read model."""

    id: str
    venture_id: str
    name: str
    status: str
    icp: dict | None = None
    positioning: dict | None = None
    pricing: dict | None = None
    messaging: dict | None = None
    objection_rebuttals: list[dict] | None = None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# ICP (Ideal Customer Profile)
# ------------------------------------------------------------------


class ICPRequest(BaseModel):
    """Request to generate an Ideal Customer Profile."""

    offer_id: str
    domain: str
    initial_description: str


class ICPResult(BaseModel):
    """Generated ICP with behavioral, firmographic, psychographic attributes."""

    offer_id: str
    icp: dict = Field(
        ...,
        description="Behavioral, firmographic, and psychographic attributes",
    )


# ------------------------------------------------------------------
# Positioning
# ------------------------------------------------------------------


class PositioningRequest(BaseModel):
    """Request to generate positioning strategy."""

    offer_id: str
    domain: str
    competitors: list[str] = Field(default_factory=list)
    differentiators: list[str] = Field(default_factory=list)


class PositioningResult(BaseModel):
    """Generated positioning: category, value prop, competitive frame."""

    offer_id: str
    positioning: dict = Field(
        ...,
        description="Category, value proposition, competitive frame",
    )


# ------------------------------------------------------------------
# Pricing
# ------------------------------------------------------------------


class PricingRequest(BaseModel):
    """Request to generate pricing strategy."""

    offer_id: str
    value_delivered: str
    target_segment: str
    competitor_pricing: list[dict] = Field(default_factory=list)


class PricingResult(BaseModel):
    """Generated pricing: model, tiers, price points, rationale."""

    offer_id: str
    pricing: dict = Field(
        ...,
        description="Model, tiers, price points, rationale",
    )


# ------------------------------------------------------------------
# Landing Page Copy
# ------------------------------------------------------------------


class LandingCopyRequest(BaseModel):
    """Request to generate conversion-optimized landing page copy."""

    offer_id: str
    persona: str = ""
    tone: str = "professional"


class LandingCopyResult(BaseModel):
    """Full landing page copy structure."""

    offer_id: str
    headline: str
    subheadline: str
    hero_body: str
    benefits: list[str]
    social_proof_frame: str
    cta_primary: str
    cta_secondary: str
    full_page_structure: list[dict]
