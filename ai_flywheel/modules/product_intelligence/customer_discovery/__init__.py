"""Customer Discovery Engine — Module #26.

Validates problem spaces through structured interviews, transcript analysis,
and cross-interview synthesis. The first use-case proving the AI Flywheel spine.
"""

from .models import Assumption, DiscoveryProject, Interview
from .schemas import (
    AssumptionUpdate,
    DiscoveryProjectCreate,
    DiscoveryProjectResponse,
    InsightItem,
    InterviewGuideRequest,
    InterviewGuideResponse,
    SynthesisRequest,
    SynthesisResponse,
    TranscriptAnalysisRequest,
    TranscriptAnalysisResponse,
)
from .service import CustomerDiscoveryEngine

__all__ = [
    # Service
    "CustomerDiscoveryEngine",
    # Models
    "Assumption",
    "DiscoveryProject",
    "Interview",
    # Schemas
    "AssumptionUpdate",
    "DiscoveryProjectCreate",
    "DiscoveryProjectResponse",
    "InsightItem",
    "InterviewGuideRequest",
    "InterviewGuideResponse",
    "SynthesisRequest",
    "SynthesisResponse",
    "TranscriptAnalysisRequest",
    "TranscriptAnalysisResponse",
]
