# ruff: noqa: E501
"""Labeling & Ground Truth — core service.

Manages labeling tasks, multi-annotator item labeling, consensus resolution,
inter-annotator agreement computation, and gold standard set retrieval.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.traces import get_tracer

from .models import LabelingTask, LabelItem
from .schemas import (
    AddItemsRequest,
    AddItemsResult,
    AgreementMetrics,
    LabelItemResponse,
    LabelRequest,
    TaskCreate,
    TaskResponse,
)

logger = structlog.get_logger()


class LabelingEngine:
    """Manages labeling tasks, annotations, consensus, and agreement metrics."""

    # ------------------------------------------------------------------
    # Task CRUD
    # ------------------------------------------------------------------

    async def create_task(self, venture_id: str, data: TaskCreate) -> TaskResponse:
        """Create a new labeling task."""
        async with get_session(venture_id) as session:
            task = LabelingTask(
                venture_id=venture_id,
                name=data.name,
                description=data.description,
                task_type=data.task_type,
                instructions=data.instructions,
                label_options=data.label_options,
                status="active",
                total_items=0,
                labeled_items=0,
            )
            session.add(task)
            await session.flush()
            await session.refresh(task)

            logger.info(
                "labeling_task_created",
                venture_id=venture_id,
                task_id=task.id,
                name=data.name,
                task_type=data.task_type,
            )

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="labeling.task.created",
                source_module="labeling_engine",
                payload={
                    "task_id": task.id,
                    "name": data.name,
                    "task_type": data.task_type,
                },
                venture_id=venture_id,
            )

            return self._task_to_response(task)

    async def get_task(self, venture_id: str, task_id: str) -> TaskResponse:
        """Retrieve a labeling task by ID."""
        async with get_session(venture_id) as session:
            stmt = (
                select(LabelingTask)
                .where(LabelingTask.id == task_id)
                .where(LabelingTask.venture_id == venture_id)
                .where(LabelingTask.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            task = result.scalar_one()
            return self._task_to_response(task)

    async def list_tasks(self, venture_id: str) -> list[TaskResponse]:
        """List all labeling tasks for a venture."""
        async with get_session(venture_id) as session:
            stmt = (
                select(LabelingTask)
                .where(LabelingTask.venture_id == venture_id)
                .where(LabelingTask.deleted_at.is_(None))
                .order_by(LabelingTask.created_at.desc())
            )
            result = await session.execute(stmt)
            tasks = result.scalars().all()
            return [self._task_to_response(t) for t in tasks]

    # ------------------------------------------------------------------
    # Item Management
    # ------------------------------------------------------------------

    async def add_items(
        self, venture_id: str, request: AddItemsRequest
    ) -> AddItemsResult:
        """Add items to a labeling task."""
        async with get_session(venture_id) as session:
            # Verify task exists
            stmt = (
                select(LabelingTask)
                .where(LabelingTask.id == request.task_id)
                .where(LabelingTask.venture_id == venture_id)
                .where(LabelingTask.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            task = result.scalar_one()

            items_added = 0
            for item_content in request.items:
                item = LabelItem(
                    venture_id=venture_id,
                    task_id=task.id,
                    content=item_content,
                    labels=[],
                    consensus_label=None,
                    is_gold=request.is_gold,
                    status="pending",
                )
                session.add(item)
                items_added += 1

            # Update task counts
            task.total_items = task.total_items + items_added
            await session.flush()

            logger.info(
                "labeling_items_added",
                venture_id=venture_id,
                task_id=task.id,
                items_added=items_added,
                is_gold=request.is_gold,
            )

            return AddItemsResult(task_id=task.id, items_added=items_added)

    # ------------------------------------------------------------------
    # Labeling
    # ------------------------------------------------------------------

    async def label_item(
        self, venture_id: str, request: LabelRequest
    ) -> LabelItemResponse:
        """Add a label annotation to an item. Resolves consensus if 2+ annotators agree."""
        event_bus = get_event_bus()
        tracer = get_tracer()

        async with tracer.span(
            "labeling_engine", "label_item", input_data={"item_id": request.item_id}
        ):
            async with get_session(venture_id) as session:
                stmt = (
                    select(LabelItem)
                    .where(LabelItem.id == request.item_id)
                    .where(LabelItem.venture_id == venture_id)
                    .where(LabelItem.deleted_at.is_(None))
                )
                result = await session.execute(stmt)
                item = result.scalar_one()

                # Add the new label annotation
                annotation: dict[str, Any] = {
                    "annotator_id": request.annotator_id,
                    "label": request.label,
                    "confidence": request.confidence,
                    "notes": request.notes,
                }
                updated_labels = list(item.labels) + [annotation]
                item.labels = updated_labels

                # Resolve consensus
                previous_status = item.status
                self._resolve_consensus(item)

                await session.flush()
                await session.refresh(item)

                # Update task labeled_items count if item just became labeled
                if previous_status == "pending" and item.status in ("labeled", "disputed"):
                    task_stmt = (
                        select(LabelingTask)
                        .where(LabelingTask.id == item.task_id)
                        .where(LabelingTask.venture_id == venture_id)
                    )
                    task_result = await session.execute(task_stmt)
                    task = task_result.scalar_one()
                    task.labeled_items = task.labeled_items + 1
                    await session.flush()

            # Emit events
            await event_bus.publish(
                event_type="labeling.item.labeled",
                source_module="labeling_engine",
                payload={
                    "item_id": item.id,
                    "task_id": item.task_id,
                    "annotator_id": request.annotator_id,
                    "label": request.label,
                },
                venture_id=venture_id,
            )

            if item.consensus_label is not None and previous_status != "labeled":
                await event_bus.publish(
                    event_type="labeling.consensus.reached",
                    source_module="labeling_engine",
                    payload={
                        "item_id": item.id,
                        "task_id": item.task_id,
                        "consensus_label": item.consensus_label,
                    },
                    venture_id=venture_id,
                )

            logger.info(
                "labeling_item_labeled",
                venture_id=venture_id,
                item_id=item.id,
                annotator_id=request.annotator_id,
                status=item.status,
                consensus_label=item.consensus_label,
            )

            return self._item_to_response(item)

    # ------------------------------------------------------------------
    # Item Retrieval
    # ------------------------------------------------------------------

    async def get_items(
        self,
        venture_id: str,
        task_id: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[LabelItemResponse]:
        """Get items for a task, optionally filtered by status."""
        async with get_session(venture_id) as session:
            stmt = (
                select(LabelItem)
                .where(LabelItem.venture_id == venture_id)
                .where(LabelItem.task_id == task_id)
                .where(LabelItem.deleted_at.is_(None))
            )
            if status is not None:
                stmt = stmt.where(LabelItem.status == status)

            stmt = stmt.order_by(LabelItem.created_at.asc()).limit(limit)
            result = await session.execute(stmt)
            items = result.scalars().all()
            return [self._item_to_response(i) for i in items]

    # ------------------------------------------------------------------
    # Agreement Metrics
    # ------------------------------------------------------------------

    async def compute_agreement(
        self, venture_id: str, task_id: str
    ) -> AgreementMetrics:
        """Compute simple inter-annotator agreement rate for a task.

        Agreement rate = % of multi-annotated items where all annotators agree.
        """
        async with get_session(venture_id) as session:
            stmt = (
                select(LabelItem)
                .where(LabelItem.venture_id == venture_id)
                .where(LabelItem.task_id == task_id)
                .where(LabelItem.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            items = result.scalars().all()

            total_items = len(items)
            items_with_consensus = 0
            items_disputed = 0
            multi_annotated = 0

            for item in items:
                labels = item.labels or []
                if len(labels) < 2:
                    continue

                multi_annotated += 1
                label_values = [lbl.get("label") for lbl in labels]
                unique_labels = set(label_values)

                if len(unique_labels) == 1:
                    items_with_consensus += 1
                else:
                    items_disputed += 1

            agreement_rate = (
                items_with_consensus / multi_annotated
                if multi_annotated > 0
                else 0.0
            )

            return AgreementMetrics(
                task_id=task_id,
                total_items=total_items,
                agreement_rate=agreement_rate,
                items_with_consensus=items_with_consensus,
                items_disputed=items_disputed,
            )

    # ------------------------------------------------------------------
    # Gold Standard
    # ------------------------------------------------------------------

    async def get_gold_set(
        self, venture_id: str, task_id: str
    ) -> list[LabelItemResponse]:
        """Return gold standard items for a task."""
        async with get_session(venture_id) as session:
            stmt = (
                select(LabelItem)
                .where(LabelItem.venture_id == venture_id)
                .where(LabelItem.task_id == task_id)
                .where(LabelItem.is_gold.is_(True))
                .where(LabelItem.deleted_at.is_(None))
                .order_by(LabelItem.created_at.asc())
            )
            result = await session.execute(stmt)
            items = result.scalars().all()
            return [self._item_to_response(i) for i in items]

    # ------------------------------------------------------------------
    # Consensus Logic
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_consensus(item: LabelItem) -> None:
        """Resolve consensus for an item based on annotator labels.

        If 2+ labels exist and majority agrees → set consensus_label, status="labeled".
        If disagreement → status="disputed".
        """
        labels = item.labels or []
        if len(labels) < 2:
            return

        label_values = [lbl.get("label") for lbl in labels if lbl.get("label")]
        if not label_values:
            return

        counter = Counter(label_values)
        most_common_label, most_common_count = counter.most_common(1)[0]

        # Majority: more than half of annotators agree
        if most_common_count > len(label_values) / 2:
            item.consensus_label = most_common_label
            item.status = "labeled"
        else:
            item.status = "disputed"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _task_to_response(task: LabelingTask) -> TaskResponse:
        """Convert a task model to response schema."""
        return TaskResponse(
            id=task.id,
            venture_id=task.venture_id,
            name=task.name,
            description=task.description,
            task_type=task.task_type,
            instructions=task.instructions,
            label_options=task.label_options or [],
            status=task.status,
            total_items=task.total_items,
            labeled_items=task.labeled_items,
            created_at=task.created_at,
        )

    @staticmethod
    def _item_to_response(item: LabelItem) -> LabelItemResponse:
        """Convert a label item model to response schema."""
        return LabelItemResponse(
            id=item.id,
            task_id=item.task_id,
            content=item.content,
            labels=item.labels or [],
            consensus_label=item.consensus_label,
            is_gold=item.is_gold,
            status=item.status,
            created_at=item.created_at,
        )
