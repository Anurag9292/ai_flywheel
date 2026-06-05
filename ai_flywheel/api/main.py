"""FastAPI application — the HTTP interface to the platform."""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_flywheel import __version__
from ai_flywheel.api.routers import (
    agents,
    auth,
    blueprints,
    costs,
    deployments,
    discovery,
    embeddings,
    experiments,
    feedback,
    health,
    ingest,
    knowledge_graph,
    market,
    memory,
    ml,
    offers,
    patterns,
    policies,
    product,
    prompts,
    quality,
    reviews,
    thesis,
    tools,
    ventures,
    workflows,
)
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

# CORS — allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from ai_flywheel.api.middleware.venture_context import VentureContextMiddleware
app.add_middleware(VentureContextMiddleware)

# Register routers
app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(ventures.router, prefix="/api/ventures", tags=["ventures"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(discovery.router, prefix="/api/discovery", tags=["discovery"])
app.include_router(experiments.router, prefix="/api/experiments", tags=["experiments"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["prompts"])
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(policies.router, prefix="/api/policies", tags=["policies"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["ingest"])
app.include_router(quality.router, prefix="/api/quality", tags=["quality"])
app.include_router(embeddings.router, prefix="/api/embeddings", tags=["embeddings"])
app.include_router(knowledge_graph.router, prefix="/api/knowledge-graph", tags=["knowledge-graph"])
app.include_router(market.router, prefix="/api/market", tags=["market"])
app.include_router(thesis.router, prefix="/api/thesis", tags=["thesis"])
app.include_router(offers.router, prefix="/api/offers", tags=["offers"])
app.include_router(product.router, prefix="/api/product", tags=["product"])
app.include_router(blueprints.router, prefix="/api/blueprints", tags=["blueprints"])
app.include_router(costs.router, prefix="/api/costs", tags=["costs"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
app.include_router(ml.router, prefix="/api/ml", tags=["ml"])
app.include_router(deployments.router, prefix="/api/deployments", tags=["deployments"])
app.include_router(patterns.router, prefix="/api/patterns", tags=["patterns"])
