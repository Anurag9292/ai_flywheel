"""Pydantic schemas for Workflow Blueprint Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

# ------------------------------------------------------------------
# Blueprint CRUD
# ------------------------------------------------------------------


class BlueprintCreate(BaseModel):
    """Request to create a new workflow blueprint."""

    name: str
    description: str


class BlueprintResponse(BaseModel):
    """Full workflow blueprint response."""

    id: str
    venture_id: str
    name: str
    description: str
    status: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    sla_config: dict[str, Any] | None
    fallback_config: dict[str, Any] | None
    version: int
    created_at: datetime
    updated_at: datetime


# ------------------------------------------------------------------
# Generate Blueprint from Description
# ------------------------------------------------------------------


class GenerateBlueprintRequest(BaseModel):
    """Request to generate a workflow blueprint from natural language."""

    name: str
    process_description: str
    constraints: list[str] = []


class GenerateBlueprintResult(BaseModel):
    """Result of LLM-generated workflow blueprint."""

    blueprint_id: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    summary: str
    human_steps: int
    ai_steps: int
    tool_steps: int


# ------------------------------------------------------------------
# Node & Edge Specs
# ------------------------------------------------------------------


class NodeSpec(BaseModel):
    """Specification for a workflow node."""

    id: str
    name: str
    node_type: str  # ai_agent | human | tool | decision | start | end
    config: dict[str, Any] = {}
    inputs: list[str] = []
    outputs: list[str] = []
    sla_seconds: int | None = None


class EdgeSpec(BaseModel):
    """Specification for an edge connecting two nodes."""

    source_node_id: str
    target_node_id: str
    condition: str | None = None


# ------------------------------------------------------------------
# Validate Blueprint
# ------------------------------------------------------------------


class ValidateBlueprintRequest(BaseModel):
    """Request to validate a workflow blueprint for structural correctness."""

    blueprint_id: str


class ValidateBlueprintResult(BaseModel):
    """Result of blueprint validation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    summary: dict[str, Any]


# ------------------------------------------------------------------
# Compile Blueprint
# ------------------------------------------------------------------


class CompileRequest(BaseModel):
    """Request to compile a blueprint into executable workflow config."""

    blueprint_id: str


class CompileResult(BaseModel):
    """Compiled workflow configuration for Temporal execution."""

    blueprint_id: str
    temporal_workflow_config: dict[str, Any]
    agents_required: list[str]
    tools_required: list[str]
