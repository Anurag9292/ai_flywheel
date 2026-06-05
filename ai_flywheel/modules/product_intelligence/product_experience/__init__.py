"""Product Experience Engine — Module #29.

Designs AI-native product experiences through persona modeling, feature
prioritization, AI interaction pattern recommendation, and screen architecture
generation. Phase 3 of the AI Flywheel.
"""

from .models import ProductSpec
from .schemas import (
    AIInteractionRequest,
    AIInteractionResult,
    FeaturePrioritizationRequest,
    FeaturePrioritizationResult,
    ProductSpecCreate,
    ProductSpecResponse,
    ScreenArchitectureRequest,
    ScreenArchitectureResult,
)
from .service import ProductExperienceEngine

__all__ = [
    # Service
    "ProductExperienceEngine",
    # Models
    "ProductSpec",
    # Schemas
    "AIInteractionRequest",
    "AIInteractionResult",
    "FeaturePrioritizationRequest",
    "FeaturePrioritizationResult",
    "ProductSpecCreate",
    "ProductSpecResponse",
    "ScreenArchitectureRequest",
    "ScreenArchitectureResult",
]
