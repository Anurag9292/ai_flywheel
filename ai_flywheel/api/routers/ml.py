"""Feature Factory + Model Forge + Evaluation endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.ml_evaluation.evaluation.schemas import (
    EvalRunResult,
    EvalSuiteCreate,
    EvalSuiteResponse,
    RunEvalRequest,
)
from ai_flywheel.modules.ml_evaluation.evaluation.service import EvaluationFramework
from ai_flywheel.modules.ml_evaluation.feature_factory.schemas import (
    ComputeRequest,
    ComputeResult,
    FeatureDefCreate,
    FeatureDefResponse,
    FeatureSetCreate,
    FeatureSetResponse,
)
from ai_flywheel.modules.ml_evaluation.feature_factory.service import FeatureFactory
from ai_flywheel.modules.ml_evaluation.model_forge.schemas import (
    ModelCreate,
    ModelResponse,
    PredictRequest,
    PredictResult,
    TrainRequest,
    TrainResult,
)
from ai_flywheel.modules.ml_evaluation.model_forge.service import ModelForge

router = APIRouter()
feature_factory = FeatureFactory()
model_forge = ModelForge()
eval_framework = EvaluationFramework()


# ─── Feature Factory ──────────────────────────────────────────────────────────


@router.post("/features", response_model=FeatureDefResponse)
async def create_feature(venture_id: str, data: FeatureDefCreate):
    return await feature_factory.create_feature(venture_id, data)


@router.post("/feature-sets", response_model=FeatureSetResponse)
async def create_feature_set(venture_id: str, data: FeatureSetCreate):
    return await feature_factory.create_feature_set(venture_id, data)


@router.post("/compute", response_model=ComputeResult)
async def compute(venture_id: str, request: ComputeRequest):
    return await feature_factory.compute(venture_id, request)


# ─── Model Forge ──────────────────────────────────────────────────────────────


@router.post("/models", response_model=ModelResponse)
async def create_model(venture_id: str, data: ModelCreate):
    return await model_forge.create_model(venture_id, data)


@router.post("/models/train", response_model=TrainResult)
async def train(venture_id: str, request: TrainRequest):
    return await model_forge.train(venture_id, request)


@router.post("/models/predict", response_model=PredictResult)
async def predict(venture_id: str, request: PredictRequest):
    return await model_forge.predict(venture_id, request)


# ─── Evaluation ───────────────────────────────────────────────────────────────


@router.post("/eval-suites", response_model=EvalSuiteResponse)
async def create_suite(venture_id: str, data: EvalSuiteCreate):
    return await eval_framework.create_suite(venture_id, data)


@router.post("/eval-suites/run", response_model=EvalRunResult)
async def run_evaluation(venture_id: str, request: RunEvalRequest):
    return await eval_framework.run_evaluation(venture_id, request)
