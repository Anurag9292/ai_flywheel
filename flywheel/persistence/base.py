"""SQLAlchemy engine + session plumbing for the real (Neon) stores.

Sync SQLAlchemy 2.0 + psycopg3, per the decisions in this feature's plan: the
runtime/bus are synchronous and ingestion is low-volume batch work, so async
buys nothing today. The store *Protocols* keep async (or any other backend)
swappable later without touching node code.

``DB_URL`` selects the database. It is the **only** thing that differs between
dev, test, and prod — point it at a Neon branch for tests, the prod Neon DB for
production. Any Postgres works; swapping providers is a connection-string change.

SQLAlchemy/psycopg are imported lazily and this module is only loaded when the
``Sql*`` stores are constructed, so the fake path (and the whole default test
suite) never requires the ``db`` extra to be installed.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any


def resolve_db_url(explicit: str | None = None) -> str:
    """Resolve the database URL from an explicit arg or ``DB_URL`` env var.

    Normalizes a bare ``postgres://`` / ``postgresql://`` to the psycopg3
    driver form ``postgresql+psycopg://`` that SQLAlchemy expects (Neon hands
    out ``postgresql://`` URLs).
    """
    url = explicit or os.environ.get("DB_URL", "")
    if not url:
        raise RuntimeError(
            "No DB_URL set. The real (Neon) stores require DB_URL "
            "(e.g. postgresql://user:pass@ep-xyz.neon.tech/db?sslmode=require). "
            "Unit tests/demo use the in-memory fakes and need no database."
        )
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


@lru_cache(maxsize=8)
def get_engine(db_url: str | None = None) -> Any:
    """Create (and cache) a SQLAlchemy Engine for ``db_url`` / ``DB_URL``.

    ``pool_pre_ping`` guards against Neon's serverless idle-suspend dropping
    pooled connections.
    """
    from sqlalchemy import create_engine

    return create_engine(resolve_db_url(db_url), pool_pre_ping=True, future=True)


def make_session_factory(db_url: str | None = None) -> Any:
    """A ``sessionmaker`` bound to the resolved engine."""
    from sqlalchemy.orm import sessionmaker

    return sessionmaker(bind=get_engine(db_url), expire_on_commit=False, future=True)


def create_all(db_url: str | None = None) -> None:
    """Create the ingestion tables (used by the gated test suite / first run).

    Production uses Alembic migrations (``flywheel/persistence/alembic``); this
    is a convenience for tests and local bootstrapping against an empty DB.
    """
    from flywheel.persistence.sql_models import Base

    Base.metadata.create_all(get_engine(db_url))
