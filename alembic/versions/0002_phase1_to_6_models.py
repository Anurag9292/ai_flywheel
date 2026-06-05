# ruff: noqa: E501
"""Phase 1-6 models: all module tables with RLS policies.

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Tables that are venture-scoped (have venture_id NOT NULL) and need RLS
VENTURE_SCOPED_TABLES = [
    "prompt_templates",
    "prompt_versions",
    "agent_blueprints",
    "tool_definitions",
    "tool_executions",
    "memory_entries",
    "review_items",
    "review_policies",
    "policies",
    "policy_violations",
    "data_sources",
    "ingestion_records",
    "quality_reports",
    "quality_rules",
    "embedding_collections",
    "embedding_documents",
    "knowledge_graphs",
    "knowledge_graph_entities",
    "knowledge_graph_relationships",
    "labeling_tasks",
    "label_items",
    "pii_detections",
    "retention_policies",
    "discovery_projects",
    "discovery_interviews",
    "discovery_assumptions",
    "market_signal_sources",
    "market_signals",
    "market_reports",
    "venture_theses",
    "thesis_assumptions",
    "thesis_evidence_items",
    "offers",
    "offer_messaging_variants",
    "product_specs",
    "workflow_blueprints",
    "cost_budgets",
    "cost_alerts",
    "ab_experiments",
    "ab_experiment_observations",
    "feedback_items",
    "feature_definitions",
    "feature_sets",
    "model_definitions",
    "training_runs",
    "eval_suites",
    "eval_runs",
    "synthetic_datasets",
    "simulations",
    "deployments",
    "deployment_events",
    "incidents",
    "health_metrics",
]

# Global tables (no RLS)
GLOBAL_TABLES = [
    "patterns",
    "pattern_applications",
    "flywheel_metrics",
    "cross_venture_insights",
]


def _base_columns():
    """Common columns for all tables (from BaseModel)."""
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def _venture_column():
    """Venture ID column for venture-scoped tables."""
    return sa.Column("venture_id", sa.String(36), nullable=False, index=True)


def upgrade() -> None:
    # --- Agent Runtime: Prompt Studio ---
    op.create_table(
        "prompt_templates",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("template_text", sa.Text, nullable=False),
        sa.Column("input_variables", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("category", sa.String(100), nullable=True, index=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("current_version", sa.Integer, nullable=False, server_default="1"),
    )

    op.create_table(
        "prompt_versions",
        *_base_columns(),
        _venture_column(),
        sa.Column("template_id", sa.String(36), sa.ForeignKey("prompt_templates.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("template_text", sa.Text, nullable=False),
        sa.Column("input_variables", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("change_description", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
    )

    # --- Agent Runtime: Agent Factory ---
    op.create_table(
        "agent_blueprints",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("agent_type", sa.String(50), nullable=False, server_default="single"),
        sa.Column("model", sa.String(100), nullable=False, server_default="gpt-4o-mini"),
        sa.Column("system_prompt", sa.Text, nullable=True),
        sa.Column("tools", postgresql.JSONB, nullable=True, server_default="[]"),
        sa.Column("memory_tiers", postgresql.JSONB, nullable=True, server_default="{}"),
        sa.Column("max_tokens", sa.Integer, nullable=False, server_default="4096"),
        sa.Column("temperature", sa.Float, nullable=False, server_default="0.7"),
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="120"),
        sa.Column("retry_policy", postgresql.JSONB, nullable=True, server_default='{"maximum_attempts": 3, "backoff_coefficient": 2.0}'),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )

    # --- Agent Runtime: Tool Forge ---
    op.create_table(
        "tool_definitions",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(50), nullable=False, server_default="custom"),
        sa.Column("input_schema", postgresql.JSONB, nullable=True, server_default="{}"),
        sa.Column("output_schema", postgresql.JSONB, nullable=True, server_default="{}"),
        sa.Column("config", postgresql.JSONB, nullable=True, server_default="{}"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("reliability_score", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("avg_latency_ms", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("total_invocations", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "tool_executions",
        *_base_columns(),
        _venture_column(),
        sa.Column("tool_id", sa.String(36), nullable=False, index=True),
        sa.Column("agent_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("input_data", postgresql.JSONB, nullable=True),
        sa.Column("output_data", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("cost_usd", sa.Float, nullable=False, server_default="0.0"),
    )

    # --- Agent Runtime: Memory Engine ---
    op.create_table(
        "memory_entries",
        *_base_columns(),
        _venture_column(),
        sa.Column("agent_id", sa.String, nullable=True, index=True),
        sa.Column("memory_tier", sa.String(20), nullable=False, index=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("importance", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("access_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True, server_default="{}"),
        sa.Column("embedding_vector", postgresql.JSONB, nullable=True),
    )

    # --- Agent Runtime: Human Review ---
    op.create_table(
        "review_items",
        *_base_columns(),
        _venture_column(),
        sa.Column("item_type", sa.String(50), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", index=True),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium", index=True),
        sa.Column("content", postgresql.JSONB, nullable=False),
        sa.Column("context", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("source_agent_id", sa.String, nullable=True, index=True),
        sa.Column("source_workflow_id", sa.String, nullable=True, index=True),
        sa.Column("assigned_to", sa.String, nullable=True, index=True),
        sa.Column("decision", sa.String(20), nullable=True),
        sa.Column("reviewer_notes", sa.Text, nullable=True),
        sa.Column("edited_content", postgresql.JSONB, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "review_policies",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("trigger_condition", postgresql.JSONB, nullable=False),
        sa.Column("routing", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )

    # --- Agent Runtime: Policy Engine ---
    op.create_table(
        "policies",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("policy_type", sa.String(50), nullable=False, index=True),
        sa.Column("rules", postgresql.JSONB, nullable=False),
        sa.Column("enforcement", sa.String(20), nullable=False, server_default="warn"),
        sa.Column("scope", postgresql.JSONB, nullable=False, server_default='{"all": true}'),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("violation_count", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "policy_violations",
        *_base_columns(),
        _venture_column(),
        sa.Column("policy_id", sa.String(36), sa.ForeignKey("policies.id"), nullable=False, index=True),
        sa.Column("agent_id", sa.String, nullable=True, index=True),
        sa.Column("module_name", sa.String(100), nullable=False, index=True),
        sa.Column("action_attempted", sa.Text, nullable=False),
        sa.Column("violation_details", postgresql.JSONB, nullable=False),
        sa.Column("enforcement_action", sa.String(20), nullable=False),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default="false"),
    )

    # --- Data & Knowledge: Ingestor ---
    op.create_table(
        "data_sources",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("last_ingestion_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("record_count", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "ingestion_records",
        *_base_columns(),
        _venture_column(),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("data_sources.id"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("format_detected", sa.String(50), nullable=True),
        sa.Column("records_processed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("records_failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("file_size_bytes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
    )

    # --- Data & Knowledge: Quality ---
    op.create_table(
        "quality_reports",
        *_base_columns(),
        _venture_column(),
        sa.Column("source_id", sa.String, nullable=True),
        sa.Column("dataset_name", sa.String, nullable=False),
        sa.Column("total_records", sa.Integer, nullable=False),
        sa.Column("valid_records", sa.Integer, nullable=False),
        sa.Column("invalid_records", sa.Integer, nullable=False),
        sa.Column("quality_score", sa.Float, nullable=False),
        sa.Column("completeness_score", sa.Float, nullable=False),
        sa.Column("consistency_score", sa.Float, nullable=False),
        sa.Column("freshness_score", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("issues", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("field_profiles", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("run_duration_ms", sa.Float, nullable=False, server_default="0.0"),
    )

    op.create_table(
        "quality_rules",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("rule_type", sa.String, nullable=False),
        sa.Column("field_name", sa.String, nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("severity", sa.String, nullable=False, server_default="error"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )

    # --- Data & Knowledge: Embeddings ---
    op.create_table(
        "embedding_collections",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False, server_default="text-embedding-3-small"),
        sa.Column("dimensions", sa.Integer, nullable=False, server_default="1536"),
        sa.Column("chunk_strategy", sa.String(50), nullable=False, server_default="paragraph"),
        sa.Column("chunk_size", sa.Integer, nullable=False, server_default="512"),
        sa.Column("chunk_overlap", sa.Integer, nullable=False, server_default="50"),
        sa.Column("document_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
    )

    op.create_table(
        "embedding_documents",
        *_base_columns(),
        _venture_column(),
        sa.Column("collection_id", sa.String(36), sa.ForeignKey("embedding_collections.id"), nullable=False),
        sa.Column("source_id", sa.String(36), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("embedding_vector", postgresql.JSONB, nullable=True),
    )

    # --- Data & Knowledge: Knowledge Graph ---
    op.create_table(
        "knowledge_graphs",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True, server_default=""),
        sa.Column("entity_types", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("relationship_types", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("entity_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("relationship_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(50), nullable=False, server_default="building"),
    )

    op.create_table(
        "knowledge_graph_entities",
        *_base_columns(),
        _venture_column(),
        sa.Column("graph_id", sa.String(36), sa.ForeignKey("knowledge_graphs.id"), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("properties", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("source_document_id", sa.String(36), nullable=True),
        sa.Column("mentions", sa.Integer, nullable=False, server_default="1"),
    )

    op.create_table(
        "knowledge_graph_relationships",
        *_base_columns(),
        _venture_column(),
        sa.Column("graph_id", sa.String(36), sa.ForeignKey("knowledge_graphs.id"), nullable=False),
        sa.Column("source_entity_id", sa.String(36), sa.ForeignKey("knowledge_graph_entities.id"), nullable=False),
        sa.Column("target_entity_id", sa.String(36), sa.ForeignKey("knowledge_graph_entities.id"), nullable=False),
        sa.Column("relationship_type", sa.String(100), nullable=False),
        sa.Column("properties", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("source_document_id", sa.String(36), nullable=True),
    )

    # --- Data & Knowledge: Labeling ---
    op.create_table(
        "labeling_tasks",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("task_type", sa.String, nullable=False),
        sa.Column("instructions", sa.Text, nullable=True),
        sa.Column("label_options", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String, nullable=False, server_default="active"),
        sa.Column("total_items", sa.Integer, nullable=False, server_default="0"),
        sa.Column("labeled_items", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "label_items",
        *_base_columns(),
        _venture_column(),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("labeling_tasks.id"), nullable=False),
        sa.Column("content", postgresql.JSONB, nullable=False),
        sa.Column("labels", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("consensus_label", sa.String, nullable=True),
        sa.Column("is_gold", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("status", sa.String, nullable=False, server_default="pending"),
    )

    # --- Data & Knowledge: Privacy ---
    op.create_table(
        "pii_detections",
        *_base_columns(),
        _venture_column(),
        sa.Column("source_module", sa.String, nullable=False),
        sa.Column("content_hash", sa.String, nullable=False),
        sa.Column("detections", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("action_taken", sa.String, nullable=False, server_default="none"),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "retention_policies",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("data_category", sa.String, nullable=False),
        sa.Column("retention_days", sa.Integer, nullable=False),
        sa.Column("action_on_expiry", sa.String, nullable=False, server_default="anonymize"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )

    # --- Product Intelligence: Customer Discovery ---
    op.create_table(
        "discovery_projects",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("hypothesis", sa.Text, nullable=False),
        sa.Column("assumptions", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("interview_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="0.0"),
    )

    op.create_table(
        "discovery_interviews",
        *_base_columns(),
        _venture_column(),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("discovery_projects.id"), nullable=False, index=True),
        sa.Column("interviewee_role", sa.String(255), nullable=False),
        sa.Column("transcript", sa.Text, nullable=False),
        sa.Column("extracted_insights", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("sentiment", sa.String(50), nullable=False, server_default="neutral"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "discovery_assumptions",
        *_base_columns(),
        _venture_column(),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("discovery_projects.id"), nullable=False, index=True),
        sa.Column("statement", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="unvalidated"),
        sa.Column("evidence_for", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("evidence_against", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
    )

    # --- Product Intelligence: Market Intelligence ---
    op.create_table(
        "market_signal_sources",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("url", sa.String(2048), nullable=True),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "market_signals",
        *_base_columns(),
        _venture_column(),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("market_signal_sources.id"), nullable=True),
        sa.Column("signal_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("relevance_score", sa.Float, nullable=False),
        sa.Column("impact_score", sa.Float, nullable=False),
        sa.Column("raw_data", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "market_reports",
        *_base_columns(),
        _venture_column(),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("period", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("signals_analyzed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("key_findings", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("recommendations", postgresql.JSONB, nullable=False, server_default="[]"),
    )

    # --- Product Intelligence: Venture Thesis ---
    op.create_table(
        "venture_theses",
        *_base_columns(),
        _venture_column(),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("hypothesis", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("evidence_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("assumptions", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("kill_signals", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("validation_plan", postgresql.JSONB, nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
    )

    op.create_table(
        "thesis_assumptions",
        *_base_columns(),
        _venture_column(),
        sa.Column("thesis_id", sa.String(36), sa.ForeignKey("venture_theses.id"), nullable=False, index=True),
        sa.Column("statement", sa.Text, nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="untested"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("evidence", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("validation_method", sa.String(255), nullable=True),
        sa.Column("experiment_ids", postgresql.JSONB, nullable=False, server_default="[]"),
    )

    op.create_table(
        "thesis_evidence_items",
        *_base_columns(),
        _venture_column(),
        sa.Column("thesis_id", sa.String(36), sa.ForeignKey("venture_theses.id"), nullable=False, index=True),
        sa.Column("assumption_id", sa.String(36), sa.ForeignKey("thesis_assumptions.id"), nullable=True, index=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("strength", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- Product Intelligence: Offer Design ---
    op.create_table(
        "offers",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("icp", postgresql.JSONB, nullable=True),
        sa.Column("positioning", postgresql.JSONB, nullable=True),
        sa.Column("pricing", postgresql.JSONB, nullable=True),
        sa.Column("messaging", postgresql.JSONB, nullable=True),
        sa.Column("objection_rebuttals", postgresql.JSONB, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )

    op.create_table(
        "offer_messaging_variants",
        *_base_columns(),
        _venture_column(),
        sa.Column("offer_id", sa.String(36), sa.ForeignKey("offers.id"), nullable=False, index=True),
        sa.Column("variant_name", sa.String(100), nullable=False),
        sa.Column("target_persona", sa.String(255), nullable=False),
        sa.Column("headline", sa.String(500), nullable=False),
        sa.Column("subheadline", sa.String(500), nullable=False, server_default=""),
        sa.Column("body_copy", sa.Text, nullable=False, server_default=""),
        sa.Column("cta", sa.String(255), nullable=False),
        sa.Column("conversion_rate", sa.Float, nullable=True),
        sa.Column("is_control", sa.Boolean, nullable=False, server_default="false"),
    )

    # --- Product Intelligence: Product Experience ---
    op.create_table(
        "product_specs",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("personas", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("features", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("ai_interaction_patterns", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("screen_architecture", postgresql.JSONB, nullable=True),
        sa.Column("ux_flows", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
    )

    # --- Product Intelligence: Workflow Blueprint ---
    op.create_table(
        "workflow_blueprints",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("nodes", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("edges", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("sla_config", postgresql.JSONB, nullable=True),
        sa.Column("fallback_config", postgresql.JSONB, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )

    # --- Experimentation: Cost Optimizer ---
    op.create_table(
        "cost_budgets",
        *_base_columns(),
        _venture_column(),
        sa.Column("period_type", sa.String(20), nullable=False, index=True),
        sa.Column("limit_usd", sa.Float, nullable=False),
        sa.Column("alert_threshold_pct", sa.Float, nullable=False, server_default="0.8"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )

    op.create_table(
        "cost_alerts",
        *_base_columns(),
        _venture_column(),
        sa.Column("alert_type", sa.String(20), nullable=False, index=True),
        sa.Column("budget_id", sa.String(36), sa.ForeignKey("cost_budgets.id"), nullable=True),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("current_spend_usd", sa.Float, nullable=False),
        sa.Column("limit_usd", sa.Float, nullable=False),
        sa.Column("period", sa.String(50), nullable=False),
        sa.Column("acknowledged", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Experimentation: A/B Testing ---
    op.create_table(
        "ab_experiments",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hypothesis", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft", index=True),
        sa.Column("experiment_type", sa.String(20), nullable=False, server_default="ab_test"),
        sa.Column("variants", postgresql.JSONB, nullable=False),
        sa.Column("metric_name", sa.String(255), nullable=False),
        sa.Column("metric_type", sa.String(20), nullable=False, server_default="conversion"),
        sa.Column("traffic_split", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("sample_size_target", sa.Integer, nullable=True),
        sa.Column("current_sample_size", sa.Integer, nullable=False, server_default="0"),
        sa.Column("winner", sa.String(255), nullable=True),
        sa.Column("confidence_level", sa.Float, nullable=False, server_default="0.95"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "ab_experiment_observations",
        *_base_columns(),
        _venture_column(),
        sa.Column("experiment_id", sa.String(36), sa.ForeignKey("ab_experiments.id"), nullable=False, index=True),
        sa.Column("variant_name", sa.String(255), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("context", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- Experimentation: Feedback ---
    op.create_table(
        "feedback_items",
        *_base_columns(),
        _venture_column(),
        sa.Column("feedback_type", sa.String(20), nullable=False, index=True),
        sa.Column("category", sa.String(30), nullable=False, index=True),
        sa.Column("source_module", sa.String(100), nullable=False, index=True),
        sa.Column("target_module", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.String(255), nullable=False, index=True),
        sa.Column("entity_type", sa.String(50), nullable=False, index=True),
        sa.Column("rating", sa.Float, nullable=True),
        sa.Column("correction_text", sa.Text, nullable=True),
        sa.Column("context", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("quality_score", sa.Float, nullable=False, server_default="1.0"),
    )

    # --- ML & Evaluation: Feature Factory ---
    op.create_table(
        "feature_definitions",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("input_fields", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("transform_type", sa.String(50), nullable=False),
        sa.Column("transform_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("output_dtype", sa.String(20), nullable=False, server_default="float"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )

    op.create_table(
        "feature_sets",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("feature_ids", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("record_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
    )

    # --- ML & Evaluation: Model Forge ---
    op.create_table(
        "model_definitions",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("framework", sa.String(50), nullable=False, server_default="sklearn"),
        sa.Column("algorithm", sa.String(100), nullable=False, server_default="logistic_regression"),
        sa.Column("hyperparameters", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("feature_set_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("metrics", postgresql.JSONB, nullable=True),
        sa.Column("training_duration_ms", sa.Float, nullable=True),
        sa.Column("training_samples", sa.Integer, nullable=True),
        sa.Column("artifact_path", sa.String(500), nullable=True),
    )

    op.create_table(
        "training_runs",
        *_base_columns(),
        _venture_column(),
        sa.Column("model_id", sa.String(36), sa.ForeignKey("model_definitions.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("hyperparameters", postgresql.JSONB, nullable=True),
        sa.Column("metrics", postgresql.JSONB, nullable=True),
        sa.Column("training_samples", sa.Integer, nullable=False, server_default="0"),
        sa.Column("validation_samples", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- ML & Evaluation: Evaluation ---
    op.create_table(
        "eval_suites",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("target_module", sa.String, nullable=False),
        sa.Column("metrics", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("test_cases", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String, nullable=False, server_default="active"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_score", sa.Float, nullable=True),
    )

    op.create_table(
        "eval_runs",
        *_base_columns(),
        _venture_column(),
        sa.Column("suite_id", sa.String(36), sa.ForeignKey("eval_suites.id"), nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="running"),
        sa.Column("scores", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("total_cases", sa.Integer, nullable=False, server_default="0"),
        sa.Column("passed_cases", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_cases", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- ML & Evaluation: Synthetic Data ---
    op.create_table(
        "synthetic_datasets",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("source_dataset_name", sa.String, nullable=True),
        sa.Column("generation_method", sa.String, nullable=False, server_default="statistical"),
        sa.Column("record_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("schema_definition", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String, nullable=False, server_default="generating"),
    )

    # --- ML & Evaluation: Simulation ---
    op.create_table(
        "simulations",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("workflow_blueprint_id", sa.String, nullable=True),
        sa.Column("scenarios", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String, nullable=False, server_default="draft"),
        sa.Column("results", postgresql.JSONB, nullable=True),
        sa.Column("total_scenarios", sa.Integer, nullable=False, server_default="0"),
        sa.Column("passed_scenarios", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_scenarios", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Float, nullable=True),
        sa.Column("cost_estimate_usd", sa.Float, nullable=True),
    )

    # --- Deployment: Deployment Engine ---
    op.create_table(
        "deployments",
        *_base_columns(),
        _venture_column(),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("target", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="pending"),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("url", sa.String, nullable=True),
        sa.Column("health_check_url", sa.String, nullable=True),
        sa.Column("previous_version_id", sa.String, nullable=True),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "deployment_events",
        *_base_columns(),
        _venture_column(),
        sa.Column("deployment_id", sa.String(36), sa.ForeignKey("deployments.id"), nullable=False),
        sa.Column("event_type", sa.String, nullable=False),
        sa.Column("details", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- Deployment: Reliability ---
    op.create_table(
        "incidents",
        *_base_columns(),
        _venture_column(),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("severity", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="open"),
        sa.Column("source_module", sa.String, nullable=True),
        sa.Column("affected_deployments", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("detection_method", sa.String, nullable=False, server_default="manual"),
        sa.Column("resolution", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Float, nullable=True),
    )

    op.create_table(
        "health_metrics",
        *_base_columns(),
        _venture_column(),
        sa.Column("deployment_id", sa.String, nullable=True),
        sa.Column("metric_name", sa.String, nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("threshold_warning", sa.Float, nullable=True),
        sa.Column("threshold_critical", sa.Float, nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="healthy"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- Cross-Venture: Pattern Library (GLOBAL — no RLS) ---
    op.create_table(
        "patterns",
        *_base_columns(),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("pattern_type", sa.String(50), nullable=False, index=True),
        sa.Column("content", postgresql.JSONB, nullable=False),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("source_venture_id", sa.String(36), nullable=True),
        sa.Column("success_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )

    op.create_table(
        "pattern_applications",
        *_base_columns(),
        sa.Column("venture_id", sa.String(36), nullable=False, index=True),
        sa.Column("pattern_id", sa.String(36), sa.ForeignKey("patterns.id"), nullable=False, index=True),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- Cross-Venture: Meta-Learning (GLOBAL — no RLS) ---
    op.create_table(
        "flywheel_metrics",
        *_base_columns(),
        sa.Column("venture_id", sa.String(36), nullable=False, index=True),
        sa.Column("metric_name", sa.String(100), nullable=False, index=True),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("period", sa.String(20), nullable=False, index=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "cross_venture_insights",
        *_base_columns(),
        sa.Column("insight_type", sa.String(50), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("evidence", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("affected_ventures", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- Row-Level Security Policies ---
    for table in VENTURE_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY venture_isolation_{table} ON {table}
            USING (venture_id = current_setting('app.current_venture_id', true))
        """)


def downgrade() -> None:
    # Drop RLS policies on venture-scoped tables
    for table in reversed(VENTURE_SCOPED_TABLES):
        op.execute(f"DROP POLICY IF EXISTS venture_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Drop global tables
    op.drop_table("cross_venture_insights")
    op.drop_table("flywheel_metrics")
    op.drop_table("pattern_applications")
    op.drop_table("patterns")

    # Drop venture-scoped tables in reverse order
    for table in reversed(VENTURE_SCOPED_TABLES):
        op.drop_table(table)
