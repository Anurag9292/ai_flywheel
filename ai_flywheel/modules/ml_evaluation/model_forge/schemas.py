# ruff: noqa: E501
"""Pydantic schemas for Model Forge."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ModelCreate(BaseModel):
    """Request to create a model definition."""

    name: str
    description: str = ""
    model_type: str  # classifier | regressor | ranker | embedder | custom
    framework: str = "sklearn"
    algorithm: str = "logistic_regression"
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    feature_set_id: str | None = None


class ModelResponse(BaseModel):
    """Full model definition response."""

    id: str
    venture_id: str
    name: str
    description: str | None
    model_type: str
    framework: str
    algorithm: str
    hyperparameters: dict[str, Any]
    feature_set_id: str | None
    status: str
    version: int
    metrics: dict[str, Any] | None
    training_duration_ms: float | None
    training_samples: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainRequest(BaseModel):
    """Request to train a model."""

    model_id: str
    training_data: list[dict[str, Any]]
    labels: list[Any]
    validation_split: float = 0.2
    hyperparameters: dict[str, Any] | None = None


class TrainResult(BaseModel):
    """Result of a training run."""

    run_id: str
    model_id: str
    status: str
    metrics: dict[str, Any]
    training_samples: int
    validation_samples: int
    duration_ms: float


class PredictRequest(BaseModel):
    """Request to run inference."""

    model_id: str
    records: list[dict[str, Any]]


class PredictResult(BaseModel):
    """Result of a prediction."""

    model_id: str
    predictions: list[Any]
    probabilities: list[list[float]] | None = None
    model_version: int


class TrainingRunResponse(BaseModel):
    """Full training run response."""

    id: str
    model_id: str
    status: str
    hyperparameters: dict[str, Any] | None
    metrics: dict[str, Any] | None
    training_samples: int
    validation_samples: int
    duration_ms: float
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
