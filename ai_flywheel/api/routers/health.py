"""Health and readiness endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from ai_flywheel import __version__
from ai_flywheel.core.config import settings
from ai_flywheel.core.contracts.schemas import HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """Basic health check — is the service running?"""
    return HealthStatus(
        status="healthy",
        version=__version__,
        environment=settings.environment,
        database="connected",  # TODO: actual check
        redis="connected",  # TODO: actual check
        temporal="connected",  # TODO: actual check
        timestamp=datetime.now(UTC),
    )


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness check — is the service ready to accept traffic?"""
    return {"ready": True}
