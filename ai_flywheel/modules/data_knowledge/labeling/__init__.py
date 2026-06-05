"""Labeling & Ground Truth — Module #18 (Phase 4).

Provides labeling task management, multi-annotator labeling, consensus
resolution, inter-annotator agreement metrics, and gold standard sets.
"""

from .models import LabelingTask, LabelItem
from .schemas import (
    AddItemsRequest,
    AddItemsResult,
    AgreementMetrics,
    LabelItemResponse,
    LabelRequest,
    TaskCreate,
    TaskResponse,
)
from .service import LabelingEngine

__all__ = [
    "AddItemsRequest",
    "AddItemsResult",
    "AgreementMetrics",
    "LabelItem",
    "LabelItemResponse",
    "LabelRequest",
    "LabelingEngine",
    "LabelingTask",
    "TaskCreate",
    "TaskResponse",
]
