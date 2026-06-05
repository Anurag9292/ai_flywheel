"""Pattern Library + Meta-Learning endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.cross_venture.meta_learning.schemas import (
    FlywheelReport,
    RecordMetricRequest,
    VelocityReport,
)
from ai_flywheel.modules.cross_venture.meta_learning.service import MetaLearningEngine
from ai_flywheel.modules.cross_venture.pattern_library.schemas import (
    ApplyPatternRequest,
    ApplyPatternResult,
    PatternCreate,
    PatternResponse,
    PatternSearchRequest,
    PatternSearchResult,
)
from ai_flywheel.modules.cross_venture.pattern_library.service import PatternLibrary

router = APIRouter()
pattern_service = PatternLibrary()
meta_service = MetaLearningEngine()


# ─── Pattern Library ──────────────────────────────────────────────────────────


@router.post("/", response_model=PatternResponse)
async def create_pattern(data: PatternCreate):
    return await pattern_service.create_pattern(data)


@router.get("/", response_model=list[PatternResponse])
async def list_patterns(pattern_type: str | None = None):
    return await pattern_service.list_patterns(pattern_type)


@router.post("/search", response_model=PatternSearchResult)
async def search(request: PatternSearchRequest):
    return await pattern_service.search(request)


@router.post("/apply", response_model=ApplyPatternResult)
async def apply_pattern(request: ApplyPatternRequest):
    return await pattern_service.apply_pattern(request)


# ─── Flywheel / Meta-Learning ─────────────────────────────────────────────────


@router.post("/flywheel/metrics")
async def record_metric(request: RecordMetricRequest):
    return await meta_service.record_metric(request)


@router.get("/flywheel/velocity", response_model=VelocityReport)
async def get_velocity(venture_id: str):
    return await meta_service.get_velocity(venture_id)


@router.get("/flywheel/report", response_model=FlywheelReport)
async def get_flywheel_report():
    return await meta_service.get_flywheel_report()
