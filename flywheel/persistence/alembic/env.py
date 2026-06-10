"""Alembic environment for the ingestion persistence schema.

Reads the database URL from ``DB_URL`` (via ``resolve_db_url``) so the same
migrations run against any Neon branch / Postgres. A gitignored repo-root
``.env`` is auto-loaded first, so ``DB_URL`` can live there instead of being
exported in the shell. Target metadata is the ORM ``Base`` in
``flywheel/persistence/sql_models.py``, enabling autogenerate.
"""

from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool

from flywheel.env import load_dotenv_if_present
from flywheel.persistence.base import resolve_db_url
from flywheel.persistence.sql_models import Base

# Load a gitignored repo-root .env so `alembic upgrade` picks up DB_URL without
# needing `export DB_URL=...` in the shell. Shell vars still win (override=False).
load_dotenv_if_present()

config = context.config
config.set_main_option("sqlalchemy.url", resolve_db_url())

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
