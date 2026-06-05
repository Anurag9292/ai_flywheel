"""Human Review Engine — orchestrates human-in-the-loop review workflows.

Provides submission, routing, decision recording, and Temporal workflow signaling
for items that require human oversight before proceeding.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.tasks import signal_workflow
from ai_flywheel.core.traces import get_tracer
from ai_flywheel.modules.agent_runtime.human_review.models import (
    ReviewItem,
    ReviewPolicy,
)
from ai_flywheel.modules.agent_runtime.human_review.schemas import (
    ReviewDecision,
    ReviewPolicyCreate,
    ReviewPolicyResponse,
    ReviewQueue,
    ReviewRequest,
    ReviewResponse,
)

logger = structlog.get_logger()

MODULE_NAME = "human_review"


class HumanReviewEngine:
    """Manages human review workflows including submission, routing, and decisions."""

    async def submit_for_review(
        self,
        venture_id: str,
        request: ReviewRequest,
    ) -> ReviewResponse:
        """Submit an item for human review.

        Creates a review item, checks policies for routing/assignment,
        and emits a review.submitted event.
        """
        tracer = get_tracer()
        async with tracer.span(MODULE_NAME, "submit_for_review"):
            # Determine expiration
            expires_at: datetime | None = None
            if request.expires_in_hours is not None:
                expires_at = datetime.now(UTC) + timedelta(hours=request.expires_in_hours)

            # Check policies for routing
            routing = await self._resolve_routing(venture_id, request)

            async with get_session(venture_id) as session:
                item = ReviewItem(
                    venture_id=venture_id,
                    item_type=request.item_type,
                    status="pending",
                    priority=request.priority,
                    content=request.content,
                    context=request.context,
                    source_agent_id=request.source_agent_id,
                    source_workflow_id=request.source_workflow_id,
                    assigned_to=routing.get("assign_to"),
                    confidence_score=request.confidence_score,
                    expires_at=expires_at,
                )
                session.add(item)
                await session.flush()

                response = ReviewResponse.model_validate(item)

            # Emit event
            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="review.submitted",
                source_module=MODULE_NAME,
                payload={
                    "review_id": response.id,
                    "item_type": request.item_type,
                    "priority": request.priority,
                    "source_agent_id": request.source_agent_id,
                    "assigned_to": routing.get("assign_to"),
                },
                venture_id=venture_id,
            )

            logger.info(
                "review_submitted",
                review_id=response.id,
                venture_id=venture_id,
                item_type=request.item_type,
                priority=request.priority,
            )

            return response

    async def decide(
        self,
        venture_id: str,
        data: ReviewDecision,
    ) -> ReviewResponse:
        """Record a decision on a review item.

        Updates the review item with the decision, and if a source_workflow_id
        exists, signals the waiting Temporal workflow with the result.
        """
        tracer = get_tracer()
        async with tracer.span(MODULE_NAME, "decide"):
            now = datetime.now(UTC)

            # Map decision string to status
            status_map = {
                "approve": "approved",
                "reject": "rejected",
                "edit": "edited",
            }
            new_status = status_map.get(data.decision, data.decision)

            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(ReviewItem).where(
                        ReviewItem.id == data.review_id,
                        ReviewItem.venture_id == venture_id,
                    )
                )
                item = result.scalar_one_or_none()
                if item is None:
                    raise ValueError(f"Review item {data.review_id} not found")

                item.decision = data.decision
                item.status = new_status
                item.reviewer_notes = data.notes or None
                item.edited_content = data.edited_content
                item.reviewed_at = now

                await session.flush()

                source_workflow_id = item.source_workflow_id
                response = ReviewResponse.model_validate(item)

            # Signal waiting workflow if applicable
            if source_workflow_id:
                signal_payload: dict[str, Any] = {
                    "decision": data.decision,
                    "review_id": data.review_id,
                    "notes": data.notes,
                }
                if data.edited_content is not None:
                    signal_payload["edited_content"] = data.edited_content

                await signal_workflow(
                    source_workflow_id,
                    "review_completed",
                    signal_payload,
                )

            # Emit event
            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="review.decided",
                source_module=MODULE_NAME,
                payload={
                    "review_id": data.review_id,
                    "decision": data.decision,
                    "source_workflow_id": source_workflow_id,
                },
                venture_id=venture_id,
            )

            logger.info(
                "review_decided",
                review_id=data.review_id,
                venture_id=venture_id,
                decision=data.decision,
            )

            return response

    async def get_queue(
        self,
        venture_id: str,
        status: str | None = "pending",
        priority: str | None = None,
    ) -> ReviewQueue:
        """Get the review queue with optional filtering."""
        tracer = get_tracer()
        async with tracer.span(MODULE_NAME, "get_queue"):
            async with get_session(venture_id) as session:
                # Build base query
                query = select(ReviewItem).where(
                    ReviewItem.venture_id == venture_id
                )
                if status:
                    query = query.where(ReviewItem.status == status)
                if priority:
                    query = query.where(ReviewItem.priority == priority)

                query = query.order_by(ReviewItem.created_at.desc())

                result = await session.execute(query)
                items = result.scalars().all()

                # Get counts
                total_result = await session.execute(
                    select(func.count(ReviewItem.id)).where(
                        ReviewItem.venture_id == venture_id,
                    )
                )
                total = total_result.scalar() or 0

                pending_result = await session.execute(
                    select(func.count(ReviewItem.id)).where(
                        ReviewItem.venture_id == venture_id,
                        ReviewItem.status == "pending",
                    )
                )
                pending = pending_result.scalar() or 0

                # Overdue: pending items past their expires_at
                now = datetime.now(UTC)
                overdue_result = await session.execute(
                    select(func.count(ReviewItem.id)).where(
                        ReviewItem.venture_id == venture_id,
                        ReviewItem.status == "pending",
                        ReviewItem.expires_at.isnot(None),
                        ReviewItem.expires_at < now,
                    )
                )
                overdue = overdue_result.scalar() or 0

            return ReviewQueue(
                items=[ReviewResponse.model_validate(i) for i in items],
                total=total,
                pending=pending,
                overdue=overdue,
            )

    async def get_review(
        self,
        venture_id: str,
        review_id: str,
    ) -> ReviewResponse:
        """Get a single review item by ID."""
        tracer = get_tracer()
        async with tracer.span(MODULE_NAME, "get_review"):
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(ReviewItem).where(
                        ReviewItem.id == review_id,
                        ReviewItem.venture_id == venture_id,
                    )
                )
                item = result.scalar_one_or_none()
                if item is None:
                    raise ValueError(f"Review item {review_id} not found")

                return ReviewResponse.model_validate(item)

    async def create_policy(
        self,
        venture_id: str,
        data: ReviewPolicyCreate,
    ) -> ReviewPolicyResponse:
        """Create a new review policy."""
        tracer = get_tracer()
        async with tracer.span(MODULE_NAME, "create_policy"):
            async with get_session(venture_id) as session:
                policy = ReviewPolicy(
                    venture_id=venture_id,
                    name=data.name,
                    trigger_condition=data.trigger_condition,
                    routing=data.routing,
                    is_active=True,
                )
                session.add(policy)
                await session.flush()

                return ReviewPolicyResponse.model_validate(policy)

    async def list_policies(
        self,
        venture_id: str,
    ) -> list[ReviewPolicyResponse]:
        """List all review policies for a venture."""
        tracer = get_tracer()
        async with tracer.span(MODULE_NAME, "list_policies"):
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(ReviewPolicy).where(
                        ReviewPolicy.venture_id == venture_id,
                        ReviewPolicy.is_active.is_(True),
                    )
                )
                policies = result.scalars().all()

                return [ReviewPolicyResponse.model_validate(p) for p in policies]

    async def check_needs_review(
        self,
        venture_id: str,
        item_type: str,
        confidence: float | None = None,
        module: str | None = None,
    ) -> bool:
        """Evaluate active policies to determine if an item needs human review.

        Returns True if any active policy's trigger condition matches:
        - confidence < policy's confidence_below threshold
        - item_type matches the policy's item_type condition
        - policy's always flag is set
        - module matches the policy's module condition
        """
        tracer = get_tracer()
        async with tracer.span(MODULE_NAME, "check_needs_review"):
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(ReviewPolicy).where(
                        ReviewPolicy.venture_id == venture_id,
                        ReviewPolicy.is_active.is_(True),
                    )
                )
                policies = result.scalars().all()

            for policy in policies:
                condition = policy.trigger_condition

                # Always flag
                if condition.get("always"):
                    return True

                # Item type match
                if condition.get("item_type") and condition["item_type"] == item_type:
                    return True

                # Module match
                if condition.get("module") and module and condition["module"] == module:
                    return True

                # Confidence threshold
                confidence_below = condition.get("confidence_below")
                if confidence_below is not None and confidence is not None:
                    if confidence < confidence_below:
                        return True

            return False

    async def escalate_overdue(
        self,
        venture_id: str,
        hours_overdue: int = 24,
    ) -> int:
        """Find overdue pending items and bump their priority.

        Items are considered overdue if they have been pending for longer
        than `hours_overdue`. Priority is escalated: low→medium→high→critical.

        Returns the number of items escalated.
        """
        tracer = get_tracer()
        async with tracer.span(MODULE_NAME, "escalate_overdue"):
            cutoff = datetime.now(UTC) - timedelta(hours=hours_overdue)

            priority_escalation = {
                "low": "medium",
                "medium": "high",
                "high": "critical",
                "critical": "critical",
            }

            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(ReviewItem).where(
                        ReviewItem.venture_id == venture_id,
                        ReviewItem.status == "pending",
                        ReviewItem.created_at < cutoff,
                    )
                )
                overdue_items = result.scalars().all()

                escalated_count = 0
                for item in overdue_items:
                    new_priority = priority_escalation.get(item.priority, "critical")
                    if new_priority != item.priority:
                        item.priority = new_priority
                        escalated_count += 1

                await session.flush()

            # Emit event if any items were escalated
            if escalated_count > 0:
                event_bus = get_event_bus()
                await event_bus.publish(
                    event_type="review.escalated",
                    source_module=MODULE_NAME,
                    payload={
                        "escalated_count": escalated_count,
                        "hours_overdue": hours_overdue,
                    },
                    venture_id=venture_id,
                )

            logger.info(
                "review_escalation_complete",
                venture_id=venture_id,
                escalated_count=escalated_count,
                hours_overdue=hours_overdue,
            )

            return escalated_count

    async def _resolve_routing(
        self,
        venture_id: str,
        request: ReviewRequest,
    ) -> dict[str, Any]:
        """Check active policies to determine routing for a review item."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(ReviewPolicy).where(
                    ReviewPolicy.venture_id == venture_id,
                    ReviewPolicy.is_active.is_(True),
                )
            )
            policies = result.scalars().all()

        for policy in policies:
            condition = policy.trigger_condition
            matches = False

            if condition.get("always"):
                matches = True
            elif condition.get("item_type") and condition["item_type"] == request.item_type:
                matches = True
            elif condition.get("confidence_below") and request.confidence_score is not None:
                if request.confidence_score < condition["confidence_below"]:
                    matches = True

            if matches and policy.routing:
                return policy.routing

        return {}
