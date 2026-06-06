"""Venture Intelligence Store — persists all agent outputs as queryable venture context."""

from __future__ import annotations

from ai_flywheel.core.database import get_session
from sqlalchemy import text

import structlog

logger = structlog.get_logger()


class VentureIntelligenceStore:
    """Stores and retrieves all agent execution outputs for a venture."""

    async def store_output(
        self,
        venture_id: str,
        agent_id: str,
        agent_name: str,
        task: str,
        output: str,
        cost_usd: float = 0.0,
        trace_id: str | None = None,
    ) -> dict:
        """Store an agent execution output."""
        async with get_session(venture_id) as session:
            await session.execute(
                text("""
                    INSERT INTO venture_intelligence (id, venture_id, agent_id, agent_name, task, output, cost_usd, trace_id, created_at)
                    VALUES (gen_random_uuid(), :venture_id, :agent_id, :agent_name, :task, :output, :cost_usd, :trace_id, now())
                """),
                {
                    "venture_id": venture_id,
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "task": task,
                    "output": output,
                    "cost_usd": cost_usd,
                    "trace_id": trace_id,
                },
            )
        logger.info(
            "intelligence_stored",
            venture_id=venture_id,
            agent_id=agent_id,
            agent_name=agent_name,
        )
        return {"status": "stored"}

    async def get_outputs(self, venture_id: str, limit: int = 20) -> list[dict]:
        """Get recent outputs for a venture."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                text("""
                    SELECT id, agent_id, agent_name, task, output, cost_usd, trace_id, created_at
                    FROM venture_intelligence
                    WHERE venture_id = :venture_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"venture_id": venture_id, "limit": limit},
            )
            rows = result.mappings().all()
            return [dict(r) for r in rows]

    async def get_context_summary(self, venture_id: str) -> str:
        """Get a summary of all intelligence for context injection into agents."""
        outputs = await self.get_outputs(venture_id, limit=10)
        if not outputs:
            return "No previous intelligence gathered yet."

        lines = []
        for o in outputs:
            lines.append(
                f"[{o['agent_name']}] Task: {o['task'][:100]}\nOutput: {o['output'][:300]}"
            )
        return "\n\n".join(lines)
