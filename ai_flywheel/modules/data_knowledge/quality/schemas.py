"""Data Quality Engine — Pydantic schemas for API layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# --- Rule schemas ---


class QualityRuleCreate(BaseModel):
    """Schema for creating a new quality rule."""

    name: str
    rule_type: str  # not_null | type_check | range | regex | unique | custom
    field_name: str
    config: dict[str, Any] = Field(default_factory=dict)
    severity: str = "error"  # error | warning | info


class QualityRuleResponse(BaseModel):
    """Schema for returning a quality rule."""

    id: str
    venture_id: str
    name: str
    rule_type: str
    field_name: str
    config: dict[str, Any]
    severity: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Check schemas ---


class QualityCheckRequest(BaseModel):
    """Schema for requesting a quality check on a set of records."""

    records: list[dict[str, Any]]
    dataset_name: str = "unnamed"
    source_id: str | None = None
    rules: list[str] | None = None  # rule IDs; None = apply all active rules


class QualityIssue(BaseModel):
    """A single quality issue found during a check."""

    field: str
    rule: str
    severity: str
    count: int
    sample_values: list[Any]
    message: str


class FieldProfile(BaseModel):
    """Statistical profile for a single field."""

    field_name: str
    dtype: str
    non_null_count: int
    null_count: int
    unique_count: int
    min_value: Any = None
    max_value: Any = None
    mean_value: float | None = None
    sample_values: list[Any] = Field(default_factory=list)


class QualityCheckResult(BaseModel):
    """Result of a quality check run."""

    report_id: str
    dataset_name: str
    total_records: int
    valid_records: int
    invalid_records: int
    quality_score: float
    completeness_score: float
    consistency_score: float
    issues: list[QualityIssue]
    field_profiles: dict[str, FieldProfile]

    model_config = {"from_attributes": True}
