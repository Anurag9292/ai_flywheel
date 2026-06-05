"""Agent Blueprint — data-driven agent definitions stored in the database.

Agents are defined as configuration (data), not code. This enables:
- Dynamic agent creation/modification without deployments
- Version tracking for A/B testing and rollback
- Venture-scoped isolation via RLS
"""

from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class AgentBlueprint(BaseModel, VentureScopedMixin):
    """Defines an agent's configuration — model, prompt, tools, policies.

    agent_type determines orchestration behavior:
    - "single": One LLM call with system prompt + task
    - "chain": Sequential execution, output feeds into next agent
    - "parallel": Fan-out to multiple agents, merge results
    - "router": Picks the best sub-agent based on task content
    """

    __tablename__ = "agent_blueprints"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="single"
    )
    model: Mapped[str] = mapped_column(
        String(100), nullable=False, default="gpt-4o-mini"
    )
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    memory_tiers: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=4096)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    retry_policy: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=lambda: {"maximum_attempts": 3, "backoff_coefficient": 2.0}
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def __repr__(self) -> str:
        return f"<AgentBlueprint name={self.name!r} type={self.agent_type!r} v{self.version}>"
