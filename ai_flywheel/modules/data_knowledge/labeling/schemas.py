"""Labeling & Ground Truth — Pydantic schemas for API layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """Schema for creating a new labeling task."""

    name: str
    description: str = ""
    task_type: str  # classification | extraction | rating | comparison | free_text
    instructions: str = ""
    label_options: list[str] = Field(default_factory=list)


class TaskResponse(BaseModel):
    """Schema for returning a labeling task."""

    id: str
    venture_id: str
    name: str
    description: str | None
    task_type: str
    instructions: str | None
    label_options: list[str]
    status: str
    total_items: int
    labeled_items: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AddItemsRequest(BaseModel):
    """Schema for adding items to a labeling task."""

    task_id: str
    items: list[dict[str, Any]]
    is_gold: bool = False


class AddItemsResult(BaseModel):
    """Result of adding items to a task."""

    task_id: str
    items_added: int


class LabelRequest(BaseModel):
    """Schema for labeling an item."""

    item_id: str
    annotator_id: str
    label: str
    confidence: float = 1.0
    notes: str = ""


class LabelItemResponse(BaseModel):
    """Schema for returning a label item."""

    id: str
    task_id: str
    content: dict[str, Any]
    labels: list[dict[str, Any]]
    consensus_label: str | None
    is_gold: bool
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AgreementMetrics(BaseModel):
    """Inter-annotator agreement metrics for a task."""

    task_id: str
    total_items: int
    agreement_rate: float
    items_with_consensus: int
    items_disputed: int
