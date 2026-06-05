"""Market & Signal Intelligence — Module #25.

Provides LLM-powered market signal detection, analysis, report generation,
and opportunity scoring for ventures.
"""

from .models import MarketReport, MarketSignal, SignalSource
from .schemas import (
    AnalyzeSignalsRequest,
    AnalyzeSignalsResult,
    MarketReportRequest,
    MarketReportResponse,
    MarketSignalResponse,
    OpportunityScore,
    SignalSourceCreate,
    SignalSourceResponse,
)
from .service import MarketIntelligence

__all__ = [
    # Models
    "MarketReport",
    "MarketSignal",
    "SignalSource",
    # Schemas
    "AnalyzeSignalsRequest",
    "AnalyzeSignalsResult",
    "MarketReportRequest",
    "MarketReportResponse",
    "MarketSignalResponse",
    "OpportunityScore",
    "SignalSourceCreate",
    "SignalSourceResponse",
    # Service
    "MarketIntelligence",
]
