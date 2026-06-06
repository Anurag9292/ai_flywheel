"""Add venture_intelligence table for persisting agent outputs.

Revision ID: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002_phase1_to_6_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS venture_intelligence (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
            venture_id VARCHAR NOT NULL,
            agent_id VARCHAR,
            agent_name VARCHAR NOT NULL,
            task TEXT NOT NULL,
            output TEXT NOT NULL,
            cost_usd FLOAT DEFAULT 0.0,
            trace_id VARCHAR,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            CONSTRAINT fk_vi_venture FOREIGN KEY (venture_id) REFERENCES ventures(id)
        );
        CREATE INDEX IF NOT EXISTS idx_vi_venture ON venture_intelligence(venture_id, created_at DESC);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS venture_intelligence;")
