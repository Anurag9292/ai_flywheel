# ruff: noqa: E501
"""Synthetic Data Generator — core service.

Generates synthetic datasets using statistical methods, validates quality
against schema expectations, and supports augmentation of existing datasets.
"""

from __future__ import annotations

import random
import string
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus

from .models import SyntheticDataset
from .schemas import (
    AugmentRequest,
    AugmentResult,
    DatasetResponse,
    GenerateRequest,
    GenerateResult,
)

logger = structlog.get_logger()


class SyntheticDataGenerator:
    """Generates synthetic data based on schema definitions and validates quality."""

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    async def generate(
        self, venture_id: str, request: GenerateRequest
    ) -> GenerateResult:
        """Generate a synthetic dataset based on schema and method."""
        async with get_session(venture_id) as session:
            # Generate records based on schema
            records = self._generate_records(
                request.schema_definition,
                request.record_count,
                request.generation_method,
                request.seed_records,
            )

            dataset = SyntheticDataset(
                venture_id=venture_id,
                name=request.name,
                description=request.description,
                generation_method=request.generation_method,
                record_count=len(records),
                schema_definition=request.schema_definition,
                config={**request.config, "records": records},
                status="ready",
            )
            session.add(dataset)
            await session.flush()
            await session.refresh(dataset)

            logger.info(
                "synthetic_dataset_generated",
                venture_id=venture_id,
                dataset_id=dataset.id,
                name=request.name,
                record_count=len(records),
            )

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="synthetic.generated",
                source_module="synthetic_data_generator",
                payload={
                    "dataset_id": dataset.id,
                    "name": request.name,
                    "record_count": len(records),
                    "method": request.generation_method,
                },
                venture_id=venture_id,
            )

            return GenerateResult(
                dataset_id=dataset.id,
                name=dataset.name,
                records_generated=len(records),
                quality_score=None,
                status=dataset.status,
            )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_dataset(self, venture_id: str, dataset_id: str) -> DatasetResponse:
        """Get a single dataset by ID."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(SyntheticDataset).where(
                    SyntheticDataset.venture_id == venture_id,
                    SyntheticDataset.id == dataset_id,
                    SyntheticDataset.deleted_at.is_(None),
                )
            )
            dataset = result.scalar_one()
            return self._to_response(dataset)

    async def list_datasets(self, venture_id: str) -> list[DatasetResponse]:
        """List all datasets for a venture."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(SyntheticDataset).where(
                    SyntheticDataset.venture_id == venture_id,
                    SyntheticDataset.deleted_at.is_(None),
                )
            )
            datasets = result.scalars().all()
            return [self._to_response(d) for d in datasets]

    # ------------------------------------------------------------------
    # Augmentation
    # ------------------------------------------------------------------

    async def augment(
        self, venture_id: str, request: AugmentRequest
    ) -> AugmentResult:
        """Augment an existing dataset by a given factor."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(SyntheticDataset).where(
                    SyntheticDataset.venture_id == venture_id,
                    SyntheticDataset.id == request.dataset_id,
                    SyntheticDataset.deleted_at.is_(None),
                )
            )
            dataset = result.scalar_one()

            original_count = dataset.record_count
            existing_records = dataset.config.get("records", [])

            # Generate augmented records
            augmented_records = self._augment_records(
                existing_records,
                dataset.schema_definition,
                request.augmentation_type,
                request.factor,
            )

            new_count = len(augmented_records)
            total_count = original_count + new_count

            dataset.record_count = total_count
            dataset.config = {
                **dataset.config,
                "records": existing_records + augmented_records,
            }
            await session.flush()

            logger.info(
                "synthetic_dataset_augmented",
                venture_id=venture_id,
                dataset_id=dataset.id,
                original_count=original_count,
                augmented_count=new_count,
            )

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="synthetic.augmented",
                source_module="synthetic_data_generator",
                payload={
                    "dataset_id": dataset.id,
                    "original_count": original_count,
                    "augmented_count": new_count,
                    "total_count": total_count,
                },
                venture_id=venture_id,
            )

            return AugmentResult(
                dataset_id=dataset.id,
                original_count=original_count,
                augmented_count=new_count,
                total_count=total_count,
            )

    # ------------------------------------------------------------------
    # Quality Validation
    # ------------------------------------------------------------------

    async def validate_quality(self, venture_id: str, dataset_id: str) -> float:
        """Validate quality of a synthetic dataset against schema expectations."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(SyntheticDataset).where(
                    SyntheticDataset.venture_id == venture_id,
                    SyntheticDataset.id == dataset_id,
                    SyntheticDataset.deleted_at.is_(None),
                )
            )
            dataset = result.scalar_one()

            records = dataset.config.get("records", [])
            schema = dataset.schema_definition

            quality_score = self._compute_quality_score(records, schema)

            dataset.quality_score = quality_score
            dataset.status = "validated" if quality_score >= 0.7 else "rejected"
            await session.flush()

            logger.info(
                "synthetic_dataset_validated",
                venture_id=venture_id,
                dataset_id=dataset.id,
                quality_score=quality_score,
                status=dataset.status,
            )

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="synthetic.validated",
                source_module="synthetic_data_generator",
                payload={
                    "dataset_id": dataset.id,
                    "quality_score": quality_score,
                    "status": dataset.status,
                },
                venture_id=venture_id,
            )

            return quality_score

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_records(
        self,
        schema: dict[str, Any],
        count: int,
        method: str,
        seed_records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Generate synthetic records based on schema definition."""
        fields = schema.get("fields", {})
        records: list[dict[str, Any]] = []

        for _ in range(count):
            record: dict[str, Any] = {}
            for field_name, field_def in fields.items():
                field_type = field_def.get("type", "str") if isinstance(field_def, dict) else field_def
                record[field_name] = self._generate_field_value(field_type, field_def)
            records.append(record)

        return records

    def _generate_field_value(self, field_type: str, field_def: Any) -> Any:
        """Generate a random value for a field based on its type."""
        if field_type == "str" or field_type == "string":
            length = field_def.get("length", 10) if isinstance(field_def, dict) else 10
            return "".join(random.choices(string.ascii_lowercase, k=length))
        elif field_type == "int" or field_type == "integer":
            min_val = field_def.get("min", 0) if isinstance(field_def, dict) else 0
            max_val = field_def.get("max", 1000) if isinstance(field_def, dict) else 1000
            return random.randint(min_val, max_val)
        elif field_type == "float" or field_type == "number":
            mean = field_def.get("mean", 0.0) if isinstance(field_def, dict) else 0.0
            std = field_def.get("std", 1.0) if isinstance(field_def, dict) else 1.0
            return round(random.gauss(mean, std), 4)
        elif field_type == "bool" or field_type == "boolean":
            weight = field_def.get("true_weight", 0.5) if isinstance(field_def, dict) else 0.5
            return random.random() < weight
        elif field_type == "date":
            start = datetime(2020, 1, 1, tzinfo=UTC)
            end = datetime(2024, 12, 31, tzinfo=UTC)
            delta = end - start
            random_days = random.randint(0, delta.days)
            return (start + __import__("datetime").timedelta(days=random_days)).isoformat()
        else:
            return None

    def _augment_records(
        self,
        existing_records: list[dict[str, Any]],
        schema: dict[str, Any],
        augmentation_type: str,
        factor: int,
    ) -> list[dict[str, Any]]:
        """Augment existing records by generating variations."""
        augmented: list[dict[str, Any]] = []
        target_count = len(existing_records) * (factor - 1)

        if not existing_records:
            # If no existing records, generate new ones
            return self._generate_records(schema, target_count, "statistical", [])

        fields = schema.get("fields", {})
        for i in range(target_count):
            base_record = existing_records[i % len(existing_records)]
            new_record = {}
            for field_name, value in base_record.items():
                field_def = fields.get(field_name, {})
                new_record[field_name] = self._perturb_value(value, field_def, augmentation_type)
            augmented.append(new_record)

        return augmented

    def _perturb_value(self, value: Any, field_def: Any, augmentation_type: str) -> Any:
        """Apply small perturbation to a value for augmentation."""
        if isinstance(value, int):
            noise = random.randint(-max(1, abs(value) // 10), max(1, abs(value) // 10))
            return value + noise
        elif isinstance(value, float):
            noise = random.gauss(0, max(0.01, abs(value) * 0.1))
            return round(value + noise, 4)
        elif isinstance(value, str) and len(value) > 2:
            # Swap two characters or add a character
            chars = list(value)
            idx = random.randint(0, len(chars) - 2)
            chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
            return "".join(chars)
        else:
            return value

    def _compute_quality_score(self, records: list[dict[str, Any]], schema: dict[str, Any]) -> float:
        """Compute quality score by checking type conformity and completeness."""
        if not records:
            return 0.0

        fields = schema.get("fields", {})
        if not fields:
            return 1.0

        total_checks = 0
        passed_checks = 0

        for record in records:
            for field_name, field_def in fields.items():
                total_checks += 1
                field_type = field_def.get("type", "str") if isinstance(field_def, dict) else field_def

                if field_name not in record:
                    continue

                value = record[field_name]
                if self._check_type(value, field_type):
                    passed_checks += 1

        return round(passed_checks / total_checks, 4) if total_checks > 0 else 1.0

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if a value matches the expected type."""
        type_map = {
            "str": str,
            "string": str,
            "int": int,
            "integer": int,
            "float": (int, float),
            "number": (int, float),
            "bool": bool,
            "boolean": bool,
            "date": str,
        }
        expected = type_map.get(expected_type, object)
        if isinstance(expected, tuple):
            return isinstance(value, expected)
        return isinstance(value, expected)

    def _to_response(self, dataset: SyntheticDataset) -> DatasetResponse:
        """Convert ORM model to response schema."""
        return DatasetResponse(
            id=dataset.id,
            venture_id=dataset.venture_id,
            name=dataset.name,
            description=dataset.description,
            source_dataset_name=dataset.source_dataset_name,
            generation_method=dataset.generation_method,
            record_count=dataset.record_count,
            schema_definition=dataset.schema_definition,
            quality_score=dataset.quality_score,
            status=dataset.status,
            created_at=dataset.created_at,
        )
