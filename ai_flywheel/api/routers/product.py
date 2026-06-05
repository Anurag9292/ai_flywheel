"""Product Experience Engine endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.product_intelligence.product_experience.schemas import (
    AIInteractionRequest,
    AIInteractionResult,
    FeaturePrioritizationRequest,
    FeaturePrioritizationResult,
    ProductSpecCreate,
    ProductSpecResponse,
    ScreenArchitectureRequest,
    ScreenArchitectureResult,
)
from ai_flywheel.modules.product_intelligence.product_experience.service import (
    ProductExperienceEngine,
)

router = APIRouter()
service = ProductExperienceEngine()


@router.post("/specs", response_model=ProductSpecResponse)
async def create_product_spec(venture_id: str, data: ProductSpecCreate):
    return await service.create_product_spec(venture_id, data)


@router.get("/specs", response_model=list[ProductSpecResponse])
async def list_product_specs(venture_id: str):
    return await service.list_product_specs(venture_id)


@router.post("/prioritize", response_model=FeaturePrioritizationResult)
async def prioritize_features(venture_id: str, request: FeaturePrioritizationRequest):
    return await service.prioritize_features(venture_id, request)


@router.post("/ai-patterns", response_model=AIInteractionResult)
async def recommend_ai_patterns(venture_id: str, request: AIInteractionRequest):
    return await service.recommend_ai_patterns(venture_id, request)


@router.post("/screen-architecture", response_model=ScreenArchitectureResult)
async def generate_screen_architecture(venture_id: str, request: ScreenArchitectureRequest):
    return await service.generate_screen_architecture(venture_id, request)
