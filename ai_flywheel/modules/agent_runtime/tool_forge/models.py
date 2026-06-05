"""Tool Forge models — tool definitions and execution records.

Tools are external capabilities (APIs, services) that agents can invoke.
Each tool definition stores connection config, schemas, and reliability metrics.
Execution records provide an audit trail and feed the reliability score.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class ToolDefinition(BaseModel, VentureScopedMixin):
    """A registered tool that agents can invoke.

    Tools are scoped to a venture and identified by a unique name within that venture.
    The config JSONB stores connection details (base_url, auth_type, headers, etc.)
    while input_schema and output_schema define the expected parameter/return shapes.
    """

    __tablename__ = "tool_definitions"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="custom"
    )  # api|data|communication|payment|deployment|analytics|custom
    input_schema: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    output_schema: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    config: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )  # base_url, method, path, auth_type, headers, api_key, ...
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reliability_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_invocations: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return (
            f"<ToolDefinition name={self.name!r} category={self.category!r} v{self.version}>"
        )


class ToolExecution(BaseModel, VentureScopedMixin):
    """Record of a single tool invocation — success, failure, or timeout.

    Provides an audit trail for all tool usage and feeds reliability metrics
    back into the ToolDefinition.
    """

    __tablename__ = "tool_executions"

    tool_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # success|failure|timeout
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    def __repr__(self) -> str:
        return (
            f"<ToolExecution tool_id={self.tool_id!r} status={self.status!r} "
            f"duration={self.duration_ms:.1f}ms>"
        )
