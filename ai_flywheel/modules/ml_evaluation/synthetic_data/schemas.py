"""Synthetic Data Generator — Pydantic schemas for API layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Request to generate a synthetic dataset."""

    name: str
    description: str = ""
    schema_definition: dict[str, Any]
    record_count: int = 100
    generation_method: str = "statistical"
    seed_records: list[dict[str, Any]] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class GenerateResult(BaseModel):
    """Result of synthetic data generation."""

    dataset_id: str
    name: str
    records_generated: int
    quality_score: float | None
    status: str


class DatasetResponse(BaseModel):
    """Full dataset metadata response."""

    id: str
    venture_id: str
    name: str
    description: str | None
    source_dataset_name: str | None
    generation_method: str
    record_count: int
    schema_definition: dict[str, Any]
    quality_score: float | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AugmentRequest(BaseModel):
    """Request to augment an existing dataset."""

    dataset_id: str
    augmentation_type: str
    factor: int = 2
    config: dict[str, Any] = Field(default_factory=dict)


class AugmentResult(BaseModel):
    """Result of dataset augmentation."""

    dataset_id: str
    original_count: int
    augmented_count: int
    total_count: int
