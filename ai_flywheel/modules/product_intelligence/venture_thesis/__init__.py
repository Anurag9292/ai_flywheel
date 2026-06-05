"""Venture Thesis Engine — Module #27.

Manages venture thesis validation through structured evidence collection,
Bayesian-inspired confidence updating, and LLM-powered analysis. Tracks
hypotheses from creation through validation or invalidation.
"""

from .models import EvidenceItem, Thesis, ThesisAssumption
from .schemas import (
    AddEvidenceRequest,
    AssumptionCreate,
    AssumptionResponse,
    EvidenceResponse,
    ThesisCreate,
    ThesisMemoRequest,
    ThesisMemoResponse,
    ThesisResponse,
    ValidationPlanRequest,
    ValidationPlanResponse,
    ValidationStep,
)
from .service import VentureThesisEngine

__all__ = [
    # Service
    "VentureThesisEngine",
    # Models
    "EvidenceItem",
    "Thesis",
    "ThesisAssumption",
    # Schemas
    "AddEvidenceRequest",
    "AssumptionCreate",
    "AssumptionResponse",
    "EvidenceResponse",
    "ThesisCreate",
    "ThesisMemoRequest",
    "ThesisMemoResponse",
    "ThesisResponse",
    "ValidationPlanRequest",
    "ValidationPlanResponse",
    "ValidationStep",
]
