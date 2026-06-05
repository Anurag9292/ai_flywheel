# ruff: noqa: E501
"""Pydantic schemas for Feature Factory."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FeatureDefCreate(BaseModel):
    """Request to create a feature definition."""

    name: str
    description: str = ""
    input_fields: list[str]
    transform_type: str  # numeric | categorical | text | temporal | composite
    transform_config: dict[str, Any] = Field(default_factory=dict)
    output_dtype: str = "float"


class FeatureDefResponse(BaseModel):
    """Full feature definition response."""

    id: str
    venture_id: str
    name: str
    description: str | None
    input_fields: list[str]
    transform_type: str
    transform_config: dict[str, Any]
    output_dtype: str
    version: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class FeatureSetCreate(BaseModel):
    """Request to create a feature set."""

    name: str
    description: str = ""
    feature_ids: list[str]


class FeatureSetResponse(BaseModel):
    """Full feature set response."""

    id: str
    venture_id: str
    name: str
    description: str | None
    feature_ids: list[str]
    record_count: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ComputeRequest(BaseModel):
    """Request to compute features for a set of records."""

    feature_set_id: str
    records: list[dict[str, Any]]


class ComputeResult(BaseModel):
    """Result of feature computation."""

    feature_set_id: str
    computed_records: list[dict[str, Any]]
    total_records: int
    failed_records: int
    errors: list[str]


class TransformResult(BaseModel):
    """Result of previewing a single feature transform."""

    feature_name: str
    values: list[Any]
    dtype: str
