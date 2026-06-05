# ruff: noqa: E501
"""Privacy & PII Engine — core service.

Provides PII scanning, content redaction, retention policy management,
scan history, and LLM-safe content sanitization.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.traces import get_tracer

from .detectors import detect_pii
from .models import PIIDetection, RetentionPolicy
from .schemas import (
    PIIDetectionItem,
    RedactRequest,
    RedactResult,
    RetentionPolicyCreate,
    RetentionPolicyResponse,
    ScanRequest,
    ScanResult,
)

logger = structlog.get_logger()


class PrivacyEngine:
    """Manages PII detection, redaction, retention policies, and content sanitization."""

    # ------------------------------------------------------------------
    # PII Scanning
    # ------------------------------------------------------------------

    async def scan(self, venture_id: str, request: ScanRequest) -> ScanResult:
        """Scan content for PII, optionally redact, and persist the detection record."""
        tracer = get_tracer()
        event_bus = get_event_bus()

        async with tracer.span(
            "privacy_engine", "scan", input_data={"source_module": request.source_module}
        ):
            # Detect PII
            detections = detect_pii(request.content)
            has_pii = len(detections) > 0

            # Optionally redact
            redacted_content: str | None = None
            action_taken = "logged"
            if request.redact and has_pii:
                redact_result = self._redact_content(request.content, detections)
                redacted_content = redact_result.redacted_content
                action_taken = "redacted"
            elif not has_pii:
                action_taken = "none"

            # Persist detection record
            content_hash = hashlib.sha256(request.content.encode()).hexdigest()

            async with get_session(venture_id) as session:
                detection_record = PIIDetection(
                    venture_id=venture_id,
                    source_module=request.source_module,
                    content_hash=content_hash,
                    detections=[d.model_dump() for d in detections],
                    action_taken=action_taken,
                    scanned_at=datetime.now(UTC),
                )
                session.add(detection_record)
                await session.flush()

            # Emit events
            await event_bus.publish(
                event_type="privacy.scan.completed",
                source_module="privacy_engine",
                payload={
                    "source_module": request.source_module,
                    "has_pii": has_pii,
                    "detection_count": len(detections),
                    "action_taken": action_taken,
                },
                venture_id=venture_id,
            )

            if has_pii:
                pii_types = list({d.pii_type for d in detections})
                await event_bus.publish(
                    event_type="privacy.pii.detected",
                    source_module="privacy_engine",
                    payload={
                        "source_module": request.source_module,
                        "pii_types": pii_types,
                        "detection_count": len(detections),
                    },
                    venture_id=venture_id,
                )

            logger.info(
                "privacy_scan_completed",
                venture_id=venture_id,
                source_module=request.source_module,
                has_pii=has_pii,
                detection_count=len(detections),
                action_taken=action_taken,
            )

            return ScanResult(
                detections=detections,
                redacted_content=redacted_content,
                has_pii=has_pii,
                detection_count=len(detections),
            )

    # ------------------------------------------------------------------
    # Redaction
    # ------------------------------------------------------------------

    async def redact(self, venture_id: str, request: RedactRequest) -> RedactResult:
        """Replace all detected PII in content with the replacement string."""
        detections = detect_pii(request.content)
        result = self._redact_content(
            request.content, detections, replacement=request.replacement
        )

        logger.info(
            "privacy_redact_completed",
            venture_id=venture_id,
            redactions_made=result.redactions_made,
        )

        return result

    # ------------------------------------------------------------------
    # Retention Policies
    # ------------------------------------------------------------------

    async def create_retention_policy(
        self, venture_id: str, data: RetentionPolicyCreate
    ) -> RetentionPolicyResponse:
        """Create a new data retention policy."""
        async with get_session(venture_id) as session:
            policy = RetentionPolicy(
                venture_id=venture_id,
                name=data.name,
                data_category=data.data_category,
                retention_days=data.retention_days,
                action_on_expiry=data.action_on_expiry,
                is_active=True,
            )
            session.add(policy)
            await session.flush()
            await session.refresh(policy)

            logger.info(
                "retention_policy_created",
                venture_id=venture_id,
                policy_id=policy.id,
                data_category=data.data_category,
                retention_days=data.retention_days,
            )

            return RetentionPolicyResponse.model_validate(policy)

    async def list_retention_policies(
        self, venture_id: str
    ) -> list[RetentionPolicyResponse]:
        """List all active retention policies for a venture."""
        async with get_session(venture_id) as session:
            stmt = (
                select(RetentionPolicy)
                .where(RetentionPolicy.venture_id == venture_id)
                .where(RetentionPolicy.is_active.is_(True))
                .where(RetentionPolicy.deleted_at.is_(None))
                .order_by(RetentionPolicy.created_at.desc())
            )
            result = await session.execute(stmt)
            policies = result.scalars().all()
            return [RetentionPolicyResponse.model_validate(p) for p in policies]

    # ------------------------------------------------------------------
    # Scan History
    # ------------------------------------------------------------------

    async def get_scan_history(
        self, venture_id: str, source_module: str | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve scan history, optionally filtered by source module."""
        async with get_session(venture_id) as session:
            stmt = (
                select(PIIDetection)
                .where(PIIDetection.venture_id == venture_id)
                .where(PIIDetection.deleted_at.is_(None))
                .order_by(PIIDetection.scanned_at.desc())
            )
            if source_module is not None:
                stmt = stmt.where(PIIDetection.source_module == source_module)

            result = await session.execute(stmt)
            records = result.scalars().all()

            return [
                {
                    "id": r.id,
                    "source_module": r.source_module,
                    "content_hash": r.content_hash,
                    "detection_count": len(r.detections or []),
                    "action_taken": r.action_taken,
                    "scanned_at": r.scanned_at.isoformat() if r.scanned_at else None,
                }
                for r in records
            ]

    # ------------------------------------------------------------------
    # LLM Sanitization
    # ------------------------------------------------------------------

    async def sanitize_for_llm(self, text: str) -> str:
        """Convenience: scan + redact, returns clean text safe for LLM prompts.

        This method does not require a venture_id as it operates purely on text
        without persisting results.
        """
        detections = detect_pii(text)
        if not detections:
            return text

        result = self._redact_content(text, detections)
        return result.redacted_content

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _redact_content(
        content: str,
        detections: list[PIIDetectionItem],
        replacement: str = "[REDACTED]",
    ) -> RedactResult:
        """Replace all detected PII spans with the replacement string.

        Processes detections in reverse order to preserve position indices.
        """
        if not detections:
            return RedactResult(redacted_content=content, redactions_made=0)

        # Sort by start position descending to replace from end to start
        sorted_detections = sorted(detections, key=lambda d: d.start, reverse=True)
        redacted = content
        redactions_made = 0

        for detection in sorted_detections:
            redacted = redacted[: detection.start] + replacement + redacted[detection.end :]
            redactions_made += 1

        return RedactResult(
            redacted_content=redacted,
            redactions_made=redactions_made,
        )
