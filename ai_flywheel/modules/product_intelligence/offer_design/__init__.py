"""Offer Design Engine — Module #28.

AI-powered offer design including ICP profiling, competitive positioning,
pricing strategy, conversion-optimized copy, and objection handling.
"""

from .models import MessagingVariant, Offer
from .schemas import (
    ICPRequest,
    ICPResult,
    LandingCopyRequest,
    LandingCopyResult,
    OfferCreate,
    OfferResponse,
    PositioningRequest,
    PositioningResult,
    PricingRequest,
    PricingResult,
)
from .service import OfferDesignEngine

__all__ = [
    # Models
    "MessagingVariant",
    "Offer",
    # Schemas
    "ICPRequest",
    "ICPResult",
    "LandingCopyRequest",
    "LandingCopyResult",
    "OfferCreate",
    "OfferResponse",
    "PositioningRequest",
    "PositioningResult",
    "PricingRequest",
    "PricingResult",
    # Service
    "OfferDesignEngine",
]
