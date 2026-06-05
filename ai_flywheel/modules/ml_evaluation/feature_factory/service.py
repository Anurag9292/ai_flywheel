# ruff: noqa: E501
"""Feature Factory service — orchestrates feature definition, composition, and computation."""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.traces import get_tracer
from ai_flywheel.modules.ml_evaluation.feature_factory.models import (
    FeatureDefinition,
    FeatureSet,
)
from ai_flywheel.modules.ml_evaluation.feature_factory.schemas import (
    ComputeRequest,
    ComputeResult,
    FeatureDefCreate,
    FeatureDefResponse,
    FeatureSetCreate,
    FeatureSetResponse,
    TransformResult,
)
from ai_flywheel.modules.ml_evaluation.feature_factory.transforms import apply_transform

logger = structlog.get_logger()


class FeatureFactory:
    """Service for defining, composing, and computing feature transforms."""

    async def create_feature(
        self, venture_id: str, data: FeatureDefCreate
    ) -> FeatureDefResponse:
        """Create a new feature definition."""
        tracer = get_tracer()
        async with tracer.span("feature_factory", "create_feature", input_data={"name": data.name}):
            async with get_session(venture_id) as session:
                feature = FeatureDefinition(
                    venture_id=venture_id,
                    name=data.name,
                    description=data.description,
                    input_fields=data.input_fields,
                    transform_type=data.transform_type,
                    transform_config=data.transform_config,
                    output_dtype=data.output_dtype,
                )
                session.add(feature)
                await session.flush()

                response = FeatureDefResponse.model_validate(feature)

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="feature.created",
                source_module="feature_factory",
                payload={"feature_id": response.id, "name": response.name},
                venture_id=venture_id,
            )

            logger.info(
                "feature_created",
                venture_id=venture_id,
                feature_id=response.id,
                name=response.name,
                transform_type=response.transform_type,
            )
            return response

    async def list_features(self, venture_id: str) -> list[FeatureDefResponse]:
        """List all active feature definitions for a venture."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(FeatureDefinition).where(
                    FeatureDefinition.venture_id == venture_id,
                    FeatureDefinition.is_active.is_(True),
                    FeatureDefinition.deleted_at.is_(None),
                )
            )
            features = result.scalars().all()
            return [FeatureDefResponse.model_validate(f) for f in features]

    async def create_feature_set(
        self, venture_id: str, data: FeatureSetCreate
    ) -> FeatureSetResponse:
        """Create a new feature set from existing feature definitions."""
        tracer = get_tracer()
        async with tracer.span("feature_factory", "create_feature_set", input_data={"name": data.name}):
            async with get_session(venture_id) as session:
                feature_set = FeatureSet(
                    venture_id=venture_id,
                    name=data.name,
                    description=data.description,
                    feature_ids=data.feature_ids,
                    status="draft",
                )
                session.add(feature_set)
                await session.flush()

                response = FeatureSetResponse.model_validate(feature_set)

            logger.info(
                "feature_set_created",
                venture_id=venture_id,
                feature_set_id=response.id,
                name=response.name,
                feature_count=len(response.feature_ids),
            )
            return response

    async def get_feature_set(
        self, venture_id: str, feature_set_id: str
    ) -> FeatureSetResponse:
        """Get a feature set by ID."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(FeatureSet).where(
                    FeatureSet.id == feature_set_id,
                    FeatureSet.venture_id == venture_id,
                    FeatureSet.deleted_at.is_(None),
                )
            )
            feature_set = result.scalar_one()
            return FeatureSetResponse.model_validate(feature_set)

    async def compute(
        self, venture_id: str, request: ComputeRequest
    ) -> ComputeResult:
        """Apply all features in a set to each record."""
        tracer = get_tracer()
        async with tracer.span("feature_factory", "compute", input_data={"feature_set_id": request.feature_set_id, "record_count": len(request.records)}):
            # Load the feature set
            feature_set = await self.get_feature_set(venture_id, request.feature_set_id)

            # Load feature definitions
            definitions = await self._load_definitions(venture_id, feature_set.feature_ids)

            computed_records: list[dict[str, Any]] = []
            errors: list[str] = []
            failed_count = 0

            for idx, record in enumerate(request.records):
                try:
                    computed = {}
                    for defn in definitions:
                        value = apply_transform(record, defn)
                        computed[defn.name] = value
                    computed_records.append(computed)
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Record {idx}: {type(e).__name__}: {e}")
                    computed_records.append({})

            # Update feature set status and record count
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(FeatureSet).where(
                        FeatureSet.id == request.feature_set_id,
                        FeatureSet.venture_id == venture_id,
                    )
                )
                fs = result.scalar_one()
                fs.status = "ready"
                fs.record_count = len(computed_records) - failed_count

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="feature.computed",
                source_module="feature_factory",
                payload={
                    "feature_set_id": request.feature_set_id,
                    "total_records": len(request.records),
                    "failed_records": failed_count,
                },
                venture_id=venture_id,
            )

            logger.info(
                "features_computed",
                venture_id=venture_id,
                feature_set_id=request.feature_set_id,
                total=len(request.records),
                failed=failed_count,
            )

            return ComputeResult(
                feature_set_id=request.feature_set_id,
                computed_records=computed_records,
                total_records=len(request.records),
                failed_records=failed_count,
                errors=errors,
            )

    async def preview_transform(
        self, venture_id: str, feature_id: str, sample_records: list[dict[str, Any]]
    ) -> TransformResult:
        """Preview a single feature transform on sample records."""
        tracer = get_tracer()
        async with tracer.span("feature_factory", "preview_transform", input_data={"feature_id": feature_id}):
            # Load the feature definition
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(FeatureDefinition).where(
                        FeatureDefinition.id == feature_id,
                        FeatureDefinition.venture_id == venture_id,
                        FeatureDefinition.deleted_at.is_(None),
                    )
                )
                feature = result.scalar_one()
                defn = FeatureDefResponse.model_validate(feature)

            values: list[Any] = []
            for record in sample_records:
                try:
                    value = apply_transform(record, defn)
                    values.append(value)
                except Exception:
                    values.append(None)

            return TransformResult(
                feature_name=defn.name,
                values=values,
                dtype=defn.output_dtype,
            )

    async def _load_definitions(
        self, venture_id: str, feature_ids: list[str]
    ) -> list[FeatureDefResponse]:
        """Load feature definitions by IDs."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(FeatureDefinition).where(
                    FeatureDefinition.id.in_(feature_ids),
                    FeatureDefinition.venture_id == venture_id,
                    FeatureDefinition.is_active.is_(True),
                    FeatureDefinition.deleted_at.is_(None),
                )
            )
            features = result.scalars().all()
            return [FeatureDefResponse.model_validate(f) for f in features]
