"""initial ingestion schema (sources, raw_records, kg_entities, kg_edges, views)

Revision ID: 0001
Revises:
Create Date: 2026-06-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("venture_id", sa.String(), index=True, server_default=""),
        sa.Column("url", sa.String(), server_default=""),
        sa.Column("auth_ref", sa.String(), server_default=""),
        sa.Column("hints", sa.JSON()),
        sa.Column("enrichment", sa.JSON()),
        sa.Column("tags", sa.JSON()),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
        sa.Column("ingest_plan", sa.JSON(), nullable=True),
        sa.Column("schema_fingerprint", sa.String(), server_default=""),
        sa.Column("cursor", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "raw_records",
        sa.Column("ingested_seq", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.String(), index=True, server_default=""),
        sa.Column("venture_id", sa.String(), index=True, server_default=""),
        sa.Column("external_id", sa.String(), server_default=""),
        sa.Column("raw", sa.JSON()),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("source_id", "external_id", name="uq_raw_source_external"),
    )

    op.create_table(
        "kg_entities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("type", sa.String(), index=True, server_default=""),
        sa.Column("key", sa.String(), server_default=""),
        sa.Column("venture_id", sa.String(), index=True, server_default=""),
        sa.Column("props", sa.JSON()),
        sa.UniqueConstraint("venture_id", "type", "key", name="uq_entity_identity"),
    )

    op.create_table(
        "kg_edges",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("type", sa.String(), index=True, server_default=""),
        sa.Column("src_type", sa.String(), server_default=""),
        sa.Column("src_key", sa.String(), server_default=""),
        sa.Column("dst_type", sa.String(), server_default=""),
        sa.Column("dst_key", sa.String(), server_default=""),
        sa.Column("venture_id", sa.String(), index=True, server_default=""),
        sa.Column("props", sa.JSON()),
        sa.UniqueConstraint(
            "venture_id",
            "type",
            "src_type",
            "src_key",
            "dst_type",
            "dst_key",
            name="uq_edge_identity",
        ),
    )

    op.create_table(
        "materialized_views",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), index=True, server_default=""),
        sa.Column("venture_id", sa.String(), index=True, server_default=""),
        sa.Column("rows", sa.JSON()),
        sa.Column("refreshed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("venture_id", "name", name="uq_view_identity"),
    )


def downgrade() -> None:
    op.drop_table("materialized_views")
    op.drop_table("kg_edges")
    op.drop_table("kg_entities")
    op.drop_table("raw_records")
    op.drop_table("sources")
