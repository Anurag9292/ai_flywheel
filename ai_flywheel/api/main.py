"""FastAPI application — the HTTP interface to the platform."""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from ai_flywheel import __version__
from ai_flywheel.api.routers import agents, discovery, experiments, health, ventures, workflows
from ai_flywheel.core.config import settings
from ai_flywheel.core.database import close_db, init_db
from ai_flywheel.core.tasks import close_temporal_client

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — startup and shutdown hooks."""
    logger.info("app_starting", environment=settings.environment, version=__version__)
    await init_db()
    yield
    await close_db()
    await close_temporal_client()
    logger.info("app_stopped")


app = FastAPI(
    title="AI Flywheel",
    description="Personal Venture Operating System",
    version=__version__,
    lifespan=lifespan,
)

# Register routers
app.include_router(health.router, tags=["health"])
app.include_router(ventures.router, prefix="/api/ventures", tags=["ventures"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(discovery.router, prefix="/api/discovery", tags=["discovery"])
app.include_router(experiments.router, prefix="/api/experiments", tags=["experiments"])
