"""Pydantic schemas for A/B Test & Optimization Engine.

Defines the API contract for experiments, observations, and results.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExperimentCreate(BaseModel):
    """Schema for creating a new experiment."""

    name: str
    hypothesis: str
    experiment_type: str = Field(default="ab_test", pattern=r"^(ab_test|bandit|multivariate)$")
    variants: list[dict[str, Any]]
    metric_name: str
    metric_type: str = Field(default="conversion", pattern=r"^(conversion|continuous|count)$")
    confidence_level: float = Field(default=0.95, ge=0.5, le=0.99)
    sample_size_target: int | None = None


class ExperimentResponse(BaseModel):
    """Schema for experiment responses."""

    id: str
    venture_id: str
    name: str
    hypothesis: str
    status: str
    experiment_type: str
    variants: list[dict[str, Any]]
    metric_name: str
    metric_type: str
    traffic_split: dict[str, float]
    sample_size_target: int | None
    current_sample_size: int
    winner: str | None
    confidence_level: float
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecordObservationRequest(BaseModel):
    """Schema for recording an observation against an experiment variant."""

    experiment_id: str
    variant_name: str
    value: float
    user_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class VariantStats(BaseModel):
    """Statistical summary for a single variant."""

    name: str
    observations: int
    mean: float
    std_dev: float
    conversion_rate: float | None = None
    confidence_interval: tuple[float, float]


class ExperimentResults(BaseModel):
    """Full results of an experiment including statistical analysis."""

    experiment_id: str
    status: str
    variants: list[VariantStats]
    winner: str | None
    is_significant: bool
    p_value: float | None
    confidence: float
    recommendation: str
