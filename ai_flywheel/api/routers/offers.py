"""Offer Design Engine endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.product_intelligence.offer_design.schemas import (
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
from ai_flywheel.modules.product_intelligence.offer_design.service import (
    OfferDesignEngine,
)

router = APIRouter()
service = OfferDesignEngine()


@router.post("/", response_model=OfferResponse)
async def create_offer(venture_id: str, data: OfferCreate):
    return await service.create_offer(venture_id, data)


@router.get("/", response_model=list[OfferResponse])
async def list_offers(venture_id: str):
    return await service.list_offers(venture_id)


@router.post("/icp", response_model=ICPResult)
async def generate_icp(venture_id: str, request: ICPRequest):
    return await service.generate_icp(venture_id, request)


@router.post("/positioning", response_model=PositioningResult)
async def generate_positioning(venture_id: str, request: PositioningRequest):
    return await service.generate_positioning(venture_id, request)


@router.post("/pricing", response_model=PricingResult)
async def generate_pricing(venture_id: str, request: PricingRequest):
    return await service.generate_pricing(venture_id, request)


@router.post("/landing-copy", response_model=LandingCopyResult)
async def generate_landing_copy(venture_id: str, request: LandingCopyRequest):
    return await service.generate_landing_copy(venture_id, request)
