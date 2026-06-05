"""Simulation Engine — Pydantic schemas for API layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SimulationCreate(BaseModel):
    """Request to create a new simulation."""

    name: str
    description: str = ""
    workflow_blueprint_id: str | None = None
    scenarios: list[dict[str, Any]] = Field(default_factory=list)


class SimulationResponse(BaseModel):
    """Full simulation metadata response."""

    id: str
    venture_id: str
    name: str
    description: str | None
    workflow_blueprint_id: str | None
    scenarios_count: int
    status: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    duration_ms: float | None
    cost_estimate_usd: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScenarioSpec(BaseModel):
    """Specification for a single test scenario."""

    name: str
    input_data: dict[str, Any]
    expected_outcome: dict[str, Any] | None = None
    failure_injection: dict[str, Any] | None = None
    timeout_seconds: int = 60


class RunSimulationRequest(BaseModel):
    """Request to run a simulation."""

    simulation_id: str
    scenarios: list[dict[str, Any]] | None = None


class SimulationResult(BaseModel):
    """Result of running a simulation."""

    simulation_id: str
    status: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    scenario_results: list[dict[str, Any]]
    duration_ms: float
    cost_estimate_usd: float
    recommendations: list[str]
