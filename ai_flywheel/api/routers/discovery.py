"""Customer Discovery endpoints."""
from fastapi import APIRouter

from ai_flywheel.modules.product_intelligence.customer_discovery.schemas import (
    DiscoveryProjectCreate,
    DiscoveryProjectResponse,
    InterviewGuideRequest,
    InterviewGuideResponse,
    TranscriptAnalysisRequest,
    TranscriptAnalysisResponse,
)
from ai_flywheel.modules.product_intelligence.customer_discovery.service import (
    CustomerDiscoveryEngine,
)

router = APIRouter()
engine = CustomerDiscoveryEngine()


@router.post("/projects", response_model=DiscoveryProjectResponse)
async def create_project(venture_id: str, data: DiscoveryProjectCreate):
    return await engine.create_project(venture_id, data)


@router.get("/projects", response_model=list[DiscoveryProjectResponse])
async def list_projects(venture_id: str):
    return await engine.list_projects(venture_id)


@router.post("/interview-guide", response_model=InterviewGuideResponse)
async def generate_guide(venture_id: str, request: InterviewGuideRequest):
    return await engine.generate_interview_guide(venture_id, request)


@router.post("/analyze-transcript", response_model=TranscriptAnalysisResponse)
async def analyze_transcript(venture_id: str, request: TranscriptAnalysisRequest):
    return await engine.analyze_transcript(venture_id, request)
