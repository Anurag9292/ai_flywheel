"""Initial schema with RLS policies.

Revision ID: 0001
Revises: None
Create Date: 2024-01-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Ventures (global, no RLS) ---
    op.create_table(
        "ventures",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("domain", sa.Text, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("metrics_summary", postgresql.JSONB, nullable=True, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Trace Spans (venture-scoped, RLS) ---
    op.create_table(
        "trace_spans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("venture_id", sa.String(36), nullable=False, index=True),
        sa.Column("trace_id", sa.String(36), nullable=False, index=True),
        sa.Column("parent_span_id", sa.String(36), nullable=True),
        sa.Column("module_name", sa.String(100), nullable=False),
        sa.Column("operation", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ok"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Float, nullable=True),
        sa.Column("cost_usd", sa.Float, nullable=False, server_default="0"),
        sa.Column("tokens_input", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer, nullable=False, server_default="0"),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("input_data", postgresql.JSONB, nullable=True),
        sa.Column("output_data", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Cost Records (venture-scoped, RLS) ---
    op.create_table(
        "cost_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("venture_id", sa.String(36), nullable=False, index=True),
        sa.Column("module_name", sa.String(100), nullable=False, index=True),
        sa.Column("operation", sa.String(255), nullable=False),
        sa.Column("trace_span_id", sa.String(36), nullable=True),
        sa.Column("amount_usd", sa.Float, nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("tokens_input", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer, nullable=False, server_default="0"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Events (global, for audit/replay) ---
    op.create_table(
        "events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(255), nullable=False, index=True),
        sa.Column("source_module", sa.String(100), nullable=False),
        sa.Column("venture_id", sa.String(36), nullable=True, index=True),
        sa.Column("correlation_id", sa.String(36), nullable=False, index=True),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Row-Level Security Policies ---
    # Enable RLS on venture-scoped tables
    op.execute("ALTER TABLE trace_spans ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE cost_records ENABLE ROW LEVEL SECURITY")

    # Create RLS policies
    op.execute("""
        CREATE POLICY venture_isolation_trace_spans ON trace_spans
        USING (venture_id = current_setting('app.current_venture_id', true))
    """)
    op.execute("""
        CREATE POLICY venture_isolation_cost_records ON cost_records
        USING (venture_id = current_setting('app.current_venture_id', true))
    """)

    # Allow the app user to bypass RLS (for admin operations)
    # The RLS policies restrict the flywheel user; superuser bypasses by default
    op.execute("ALTER TABLE trace_spans FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE cost_records FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS venture_isolation_cost_records ON cost_records")
    op.execute("DROP POLICY IF EXISTS venture_isolation_trace_spans ON trace_spans")
    op.execute("ALTER TABLE cost_records DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE trace_spans DISABLE ROW LEVEL SECURITY")

    # Drop tables
    op.drop_table("events")
    op.drop_table("cost_records")
    op.drop_table("trace_spans")
    op.drop_table("ventures")
