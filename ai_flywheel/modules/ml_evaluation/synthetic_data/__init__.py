"""Synthetic Data Generator — Module #23 (Phase 5).

Schema-driven synthetic data generation with statistical, LLM,
and augmentation methods. Quality validation against schema expectations.
"""

from .models import SyntheticDataset
from .schemas import (
    AugmentRequest,
    AugmentResult,
    DatasetResponse,
    GenerateRequest,
    GenerateResult,
)
from .service import SyntheticDataGenerator

__all__ = [
    "AugmentRequest",
    "AugmentResult",
    "DatasetResponse",
    "GenerateRequest",
    "GenerateResult",
    "SyntheticDataGenerator",
    "SyntheticDataset",
]
