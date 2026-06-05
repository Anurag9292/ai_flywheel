"""Market & Signal Intelligence endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.product_intelligence.market_intelligence.schemas import (
    AnalyzeSignalsRequest,
    AnalyzeSignalsResult,
    MarketReportRequest,
    MarketReportResponse,
    MarketSignalResponse,
    OpportunityScore,
    SignalSourceCreate,
    SignalSourceResponse,
)
from ai_flywheel.modules.product_intelligence.market_intelligence.service import (
    MarketIntelligence,
)

router = APIRouter()
service = MarketIntelligence()


@router.post("/sources", response_model=SignalSourceResponse)
async def create_source(venture_id: str, data: SignalSourceCreate):
    return await service.create_source(venture_id, data)


@router.post("/analyze", response_model=AnalyzeSignalsResult)
async def analyze_signals(venture_id: str, request: AnalyzeSignalsRequest):
    return await service.analyze_signals(venture_id, request)


@router.post("/report", response_model=MarketReportResponse)
async def generate_report(venture_id: str, request: MarketReportRequest):
    return await service.generate_report(venture_id, request)


@router.post("/score-opportunity", response_model=OpportunityScore)
async def score_opportunity(venture_id: str, opportunity_description: str, domain: str):
    return await service.score_opportunity(venture_id, opportunity_description, domain)


@router.get("/signals", response_model=list[MarketSignalResponse])
async def get_signals(
    venture_id: str,
    signal_type: str | None = None,
    min_relevance: float = 0.0,
    limit: int = 50,
):
    return await service.get_signals(venture_id, signal_type, min_relevance, limit)
