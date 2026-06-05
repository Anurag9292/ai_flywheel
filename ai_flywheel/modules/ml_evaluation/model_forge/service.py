# ruff: noqa: E501
"""Model Forge service — orchestrates model definition, training, and inference."""

from __future__ import annotations

import hashlib
import time
from collections import Counter
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.traces import get_tracer
from ai_flywheel.modules.ml_evaluation.model_forge.models import (
    ModelDefinition,
    TrainingRun,
)
from ai_flywheel.modules.ml_evaluation.model_forge.schemas import (
    ModelCreate,
    ModelResponse,
    PredictRequest,
    PredictResult,
    TrainingRunResponse,
    TrainRequest,
    TrainResult,
)

logger = structlog.get_logger()


class ModelForge:
    """Service for defining, training, and running ML models.

    Note: Actual ML training is simulated (no sklearn/numpy/pandas imports).
    The API contract and data flow are fully implemented — real ML backends
    can be plugged in when dependencies are available.
    """

    def __init__(self) -> None:
        # In-memory storage for trained model state (simulated)
        # In production, models are serialized to artifact_path
        self._trained_models: dict[str, dict[str, Any]] = {}

    async def create_model(
        self, venture_id: str, data: ModelCreate
    ) -> ModelResponse:
        """Create a new model definition."""
        tracer = get_tracer()
        async with tracer.span("model_forge", "create_model", input_data={"name": data.name}):
            async with get_session(venture_id) as session:
                model = ModelDefinition(
                    venture_id=venture_id,
                    name=data.name,
                    description=data.description,
                    model_type=data.model_type,
                    framework=data.framework,
                    algorithm=data.algorithm,
                    hyperparameters=data.hyperparameters,
                    feature_set_id=data.feature_set_id,
                    status="draft",
                )
                session.add(model)
                await session.flush()

                response = ModelResponse.model_validate(model)

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="model.created",
                source_module="model_forge",
                payload={"model_id": response.id, "name": response.name, "model_type": response.model_type},
                venture_id=venture_id,
            )

            logger.info(
                "model_created",
                venture_id=venture_id,
                model_id=response.id,
                name=response.name,
                model_type=response.model_type,
                algorithm=response.algorithm,
            )
            return response

    async def get_model(self, venture_id: str, model_id: str) -> ModelResponse:
        """Get a model by ID."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(ModelDefinition).where(
                    ModelDefinition.id == model_id,
                    ModelDefinition.venture_id == venture_id,
                    ModelDefinition.deleted_at.is_(None),
                )
            )
            model = result.scalar_one()
            return ModelResponse.model_validate(model)

    async def list_models(
        self, venture_id: str, model_type: str | None = None
    ) -> list[ModelResponse]:
        """List models for a venture, optionally filtered by type."""
        async with get_session(venture_id) as session:
            query = select(ModelDefinition).where(
                ModelDefinition.venture_id == venture_id,
                ModelDefinition.deleted_at.is_(None),
            )
            if model_type:
                query = query.where(ModelDefinition.model_type == model_type)

            result = await session.execute(query)
            models = result.scalars().all()
            return [ModelResponse.model_validate(m) for m in models]

    async def train(self, venture_id: str, request: TrainRequest) -> TrainResult:
        """Train a model on provided data (simulated).

        In production this would use sklearn/pytorch. For now we simulate
        training by computing baseline metrics from the label distribution.
        """
        tracer = get_tracer()
        event_bus = get_event_bus()
        start_time = time.perf_counter()

        async with tracer.span("model_forge", "train", input_data={"model_id": request.model_id, "samples": len(request.training_data)}):
            # Emit training started event
            await event_bus.publish(
                event_type="model.training.started",
                source_module="model_forge",
                payload={"model_id": request.model_id, "samples": len(request.training_data)},
                venture_id=venture_id,
            )

            # Split data
            split_idx = int(len(request.training_data) * (1 - request.validation_split))
            train_data = request.training_data[:split_idx]
            val_data = request.training_data[split_idx:]
            train_labels = request.labels[:split_idx]
            val_labels = request.labels[split_idx:]

            started_at = datetime.now(UTC)

            # Simulate training — compute baseline metrics
            try:
                metrics = self._compute_baseline_metrics(train_labels, val_labels)
                status = "completed"
                error_message = None

                # Store simulated model state
                self._trained_models[request.model_id] = {
                    "train_labels": train_labels,
                    "label_distribution": dict(Counter(train_labels)),
                    "hyperparameters": request.hyperparameters or {},
                    "algorithm": "baseline",
                }
            except Exception as e:
                metrics = {}
                status = "failed"
                error_message = f"{type(e).__name__}: {e}"

            duration_ms = (time.perf_counter() - start_time) * 1000
            completed_at = datetime.now(UTC)

            # Record training run
            async with get_session(venture_id) as session:
                run = TrainingRun(
                    venture_id=venture_id,
                    model_id=request.model_id,
                    status=status,
                    hyperparameters=request.hyperparameters,
                    metrics=metrics,
                    training_samples=len(train_data),
                    validation_samples=len(val_data),
                    duration_ms=duration_ms,
                    error_message=error_message,
                    started_at=started_at,
                    completed_at=completed_at,
                )
                session.add(run)
                await session.flush()
                run_id = run.id

                # Update model definition
                model_result = await session.execute(
                    select(ModelDefinition).where(
                        ModelDefinition.id == request.model_id,
                        ModelDefinition.venture_id == venture_id,
                    )
                )
                model = model_result.scalar_one()
                model.status = "trained" if status == "completed" else "draft"
                model.metrics = metrics
                model.training_duration_ms = duration_ms
                model.training_samples = len(train_data)
                if status == "completed":
                    model.version += 1
                    # Generate a deterministic artifact path
                    artifact_hash = hashlib.md5(f"{request.model_id}:{model.version}".encode()).hexdigest()[:8]
                    model.artifact_path = f"models/{venture_id}/{request.model_id}/v{model.version}_{artifact_hash}.bin"

            # Emit training completed event
            await event_bus.publish(
                event_type="model.training.completed",
                source_module="model_forge",
                payload={
                    "model_id": request.model_id,
                    "run_id": run_id,
                    "status": status,
                    "metrics": metrics,
                    "duration_ms": duration_ms,
                },
                venture_id=venture_id,
            )

            logger.info(
                "model_training_completed",
                venture_id=venture_id,
                model_id=request.model_id,
                run_id=run_id,
                status=status,
                duration_ms=round(duration_ms, 2),
                training_samples=len(train_data),
                validation_samples=len(val_data),
            )

            return TrainResult(
                run_id=run_id,
                model_id=request.model_id,
                status=status,
                metrics=metrics,
                training_samples=len(train_data),
                validation_samples=len(val_data),
                duration_ms=round(duration_ms, 2),
            )

    async def predict(self, venture_id: str, request: PredictRequest) -> PredictResult:
        """Run inference on records (simulated).

        Uses majority-class baseline: predicts the most common label from training.
        """
        tracer = get_tracer()
        async with tracer.span("model_forge", "predict", input_data={"model_id": request.model_id, "records": len(request.records)}):
            # Get model info
            model_resp = await self.get_model(venture_id, request.model_id)

            # Get trained state
            trained_state = self._trained_models.get(request.model_id)

            if trained_state is None:
                # Model not trained — return empty predictions
                predictions = [None] * len(request.records)
                probabilities = None
            else:
                label_dist = trained_state["label_distribution"]
                total_labels = sum(label_dist.values())
                most_common = max(label_dist, key=label_dist.get)  # type: ignore[arg-type]

                # Majority class baseline prediction
                predictions = [most_common] * len(request.records)

                # Compute class probabilities from training distribution
                unique_labels = sorted(label_dist.keys(), key=str)
                prob_vector = [label_dist.get(lbl, 0) / total_labels for lbl in unique_labels]
                probabilities = [prob_vector for _ in request.records]

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="model.prediction.made",
                source_module="model_forge",
                payload={
                    "model_id": request.model_id,
                    "record_count": len(request.records),
                    "model_version": model_resp.version,
                },
                venture_id=venture_id,
            )

            logger.info(
                "model_prediction_made",
                venture_id=venture_id,
                model_id=request.model_id,
                record_count=len(request.records),
                model_version=model_resp.version,
            )

            return PredictResult(
                model_id=request.model_id,
                predictions=predictions,
                probabilities=probabilities,
                model_version=model_resp.version,
            )

    async def get_training_history(
        self, venture_id: str, model_id: str
    ) -> list[TrainingRunResponse]:
        """Get all training runs for a model."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(TrainingRun)
                .where(
                    TrainingRun.model_id == model_id,
                    TrainingRun.venture_id == venture_id,
                    TrainingRun.deleted_at.is_(None),
                )
                .order_by(TrainingRun.started_at.desc())
            )
            runs = result.scalars().all()
            return [TrainingRunResponse.model_validate(r) for r in runs]

    def _compute_baseline_metrics(
        self, train_labels: list[Any], val_labels: list[Any]
    ) -> dict[str, float]:
        """Compute baseline metrics from label distributions.

        For classification: accuracy is the majority-class ratio on validation set.
        For regression: placeholder values based on label statistics.
        """
        if not val_labels:
            return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}

        # Check if labels are numeric (regression) vs categorical (classification)
        try:
            numeric_labels = [float(v) for v in val_labels]
            numeric_train = [float(v) for v in train_labels]
            is_regression = True
        except (ValueError, TypeError):
            is_regression = False

        if is_regression:
            # Regression: compute baseline MSE/MAE using mean predictor
            if not numeric_train:
                return {"mse": 0.0, "mae": 0.0, "r2": 0.0}

            mean_pred = sum(numeric_train) / len(numeric_train)
            mse = sum((v - mean_pred) ** 2 for v in numeric_labels) / len(numeric_labels)
            mae = sum(abs(v - mean_pred) for v in numeric_labels) / len(numeric_labels)

            # R² = 1 - SS_res / SS_tot
            ss_tot = sum((v - (sum(numeric_labels) / len(numeric_labels))) ** 2 for v in numeric_labels)
            ss_res = sum((v - mean_pred) ** 2 for v in numeric_labels)
            r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

            return {
                "mse": round(mse, 4),
                "mae": round(mae, 4),
                "r2": round(r2, 4),
            }
        else:
            # Classification: majority class baseline
            train_counter = Counter(train_labels)
            most_common = train_counter.most_common(1)[0][0]

            # Accuracy = how many val labels match majority class
            correct = sum(1 for v in val_labels if v == most_common)
            accuracy = correct / len(val_labels)

            # For majority baseline, precision = accuracy, recall depends on class
            # Simplified: report accuracy-based metrics
            val_counter = Counter(val_labels)
            _num_classes = len(set(train_labels) | set(val_labels))  # noqa: F841

            # Precision for the majority class
            precision = accuracy  # All predictions are majority class
            # Recall for the majority class
            majority_in_val = val_counter.get(most_common, 0)
            recall = 1.0 if majority_in_val > 0 else 0.0  # We always predict it

            # F1
            if precision + recall > 0:
                f1 = 2 * (precision * recall) / (precision + recall)
            else:
                f1 = 0.0

            return {
                "accuracy": round(accuracy, 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
            }
