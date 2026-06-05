"""Pydantic schemas for Product Experience Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

# ------------------------------------------------------------------
# Product Spec CRUD
# ------------------------------------------------------------------


class ProductSpecCreate(BaseModel):
    """Request to create a new product specification."""

    name: str
    description: str
    target_personas: list[str] = []
    core_capabilities: list[str] = []


class ProductSpecResponse(BaseModel):
    """Full product specification response."""

    id: str
    venture_id: str
    name: str
    description: str
    personas: list[dict[str, Any]]
    features: list[dict[str, Any]]
    ai_interaction_patterns: list[dict[str, Any]]
    screen_architecture: dict[str, Any] | None
    ux_flows: list[dict[str, Any]]
    status: str
    created_at: datetime
    updated_at: datetime


# ------------------------------------------------------------------
# Feature Prioritization
# ------------------------------------------------------------------


class FeaturePrioritizationRequest(BaseModel):
    """Request to prioritize features for a product."""

    product_id: str
    features: list[dict[str, Any]]
    north_star_metric: str


class FeaturePrioritizationResult(BaseModel):
    """Result of LLM-powered feature prioritization."""

    product_id: str
    prioritized_features: list[dict[str, Any]]
    rationale: str


# ------------------------------------------------------------------
# AI Interaction Patterns
# ------------------------------------------------------------------


class AIInteractionRequest(BaseModel):
    """Request to recommend AI interaction patterns for capabilities."""

    product_id: str
    capabilities: list[str]


class AIInteractionResult(BaseModel):
    """Recommended AI interaction patterns per capability."""

    product_id: str
    patterns: list[dict[str, Any]]


# ------------------------------------------------------------------
# Screen Architecture
# ------------------------------------------------------------------


class ScreenArchitectureRequest(BaseModel):
    """Request to generate screen architecture from user goals."""

    product_id: str
    user_goals: list[str]


class ScreenArchitectureResult(BaseModel):
    """Generated screen architecture with navigation and hierarchy."""

    product_id: str
    screens: list[dict[str, Any]]
    navigation: dict[str, Any]
    information_hierarchy: list[str]
