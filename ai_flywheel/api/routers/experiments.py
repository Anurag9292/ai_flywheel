"""A/B Testing and Experimentation endpoints."""
from fastapi import APIRouter

from ai_flywheel.modules.experimentation.ab_testing.schemas import (
    ExperimentCreate,
    ExperimentResponse,
    ExperimentResults,
    RecordObservationRequest,
)
from ai_flywheel.modules.experimentation.ab_testing.service import ABTestEngine

router = APIRouter()
engine = ABTestEngine()


@router.post("/", response_model=ExperimentResponse)
async def create_experiment(venture_id: str, data: ExperimentCreate):
    return await engine.create_experiment(venture_id, data)


@router.get("/", response_model=list[ExperimentResponse])
async def list_experiments(venture_id: str, status: str | None = None):
    return await engine.list_experiments(venture_id, status)


@router.post("/{experiment_id}/observe")
async def record_observation(
    venture_id: str, experiment_id: str, request: RecordObservationRequest
):
    await engine.record_observation(venture_id, request)
    return {"status": "recorded"}


@router.get("/{experiment_id}/results", response_model=ExperimentResults)
async def get_results(venture_id: str, experiment_id: str):
    return await engine.get_results(venture_id, experiment_id)


@router.post("/{experiment_id}/start", response_model=ExperimentResponse)
async def start_experiment(venture_id: str, experiment_id: str):
    return await engine.start_experiment(venture_id, experiment_id)
