"""Evaluation Framework — Pydantic schemas for API layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MetricConfig(BaseModel):
    """Configuration for a single evaluation metric."""

    name: str
    metric_type: str  # exact_match | contains | numeric_closeness | custom
    weight: float = 1.0
    threshold: float = 0.0


class EvalSuiteCreate(BaseModel):
    """Schema for creating a new eval suite."""

    name: str
    description: str = ""
    target_module: str
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    test_cases: list[dict[str, Any]] = Field(default_factory=list)


class EvalSuiteResponse(BaseModel):
    """Schema for returning an eval suite."""

    id: str
    venture_id: str
    name: str
    description: str | None
    target_module: str
    metrics: list[dict[str, Any]]
    test_cases_count: int
    status: str
    last_run_at: datetime | None
    last_score: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RunEvalRequest(BaseModel):
    """Schema for requesting an eval run."""

    suite_id: str
    config: dict[str, Any] = Field(default_factory=dict)


class EvalRunResult(BaseModel):
    """Result of an eval run."""

    run_id: str
    suite_id: str
    status: str
    overall_score: float
    scores: dict[str, Any]
    total_cases: int
    passed_cases: int
    failed_cases: int
    duration_ms: float


class AddTestCaseRequest(BaseModel):
    """Schema for adding a test case to a suite."""

    suite_id: str
    input: dict[str, Any]
    expected_output: dict[str, Any]
    tags: list[str] = Field(default_factory=list)
