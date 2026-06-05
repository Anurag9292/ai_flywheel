"""Health and readiness endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter

from ai_flywheel import __version__
from ai_flywheel.core.config import settings

router = APIRouter()

logger = structlog.get_logger()


@router.get("/health")
async def health_check() -> dict:
    """Health check with actual connectivity status."""
    checks = {
        "database": "unknown",
        "redis": "unknown",
        "temporal": "unknown",
    }
    
    # Check database
    try:
        from ai_flywheel.core.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as e:
        checks["database"] = f"unavailable: {type(e).__name__}"
    
    # Check Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "connected"
    except Exception as e:
        checks["redis"] = f"unavailable: {type(e).__name__}"
    
    # Check Temporal
    try:
        from temporalio.client import Client
        client = await Client.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace,
        )
        checks["temporal"] = "connected"
    except Exception as e:
        checks["temporal"] = f"unavailable: {type(e).__name__}"
    
    all_healthy = all(v == "connected" for v in checks.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": __version__,
        "environment": settings.environment,
        **checks,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness check — is the service ready to accept traffic?"""
    return {"ready": True}
