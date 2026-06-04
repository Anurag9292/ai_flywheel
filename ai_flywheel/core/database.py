"""Database connection management with Row-Level Security enforcement.

Every database session MUST set the venture context before executing queries.
This ensures RLS policies isolate data at the database layer.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ai_flywheel.core.config import settings

logger = structlog.get_logger()

# Engine singleton — connection pool shared across the application
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.is_development,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_session(
    venture_id: str | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Get a database session with RLS venture context set.

    Args:
        venture_id: The venture to scope queries to. If None, RLS policies
                    will block access to venture-scoped tables (fail-closed).

    Usage:
        async with get_session(venture_id="ven_abc123") as session:
            result = await session.execute(select(Agent))
            # Only returns agents belonging to ven_abc123
    """
    async with async_session_factory() as session:
        try:
            if venture_id:
                await session.execute(
                    text("SET LOCAL app.current_venture_id = :vid"),
                    {"vid": venture_id},
                )
            else:
                await session.execute(
                    text("SET LOCAL app.current_venture_id = ''")
                )

            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_global_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a session for global (non-venture-scoped) operations.

    Use sparingly — only for platform-level operations like:
    - Creating/listing ventures
    - Managing global patterns
    - Platform configuration
    """
    async with async_session_factory() as session:
        try:
            await session.execute(
                text("SET LOCAL app.current_venture_id = ''")
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize database. Called on app startup."""
    logger.info("database_init", host=settings.database_url.split("@")[-1])


async def close_db() -> None:
    """Close database connection pool. Called on app shutdown."""
    await engine.dispose()
    logger.info("database_closed")
