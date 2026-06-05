# ruff: noqa: E501
"""Memory Engine service — multi-tier memory management for agents."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select, update

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.traces import get_tracer
from ai_flywheel.modules.agent_runtime.memory_engine.models import MemoryEntry
from ai_flywheel.modules.agent_runtime.memory_engine.schemas import (
    ConsolidateRequest,
    MemoryContext,
    MemoryQuery,
    MemoryResponse,
    MemoryStore,
)

logger = structlog.get_logger()

# Valid memory tiers
VALID_TIERS = {"working", "episodic", "semantic", "procedural"}


def _estimate_tokens(content: str) -> int:
    """Rough char-to-token ratio: ~4 chars per token."""
    return len(content) // 4


def _entry_to_response(entry: MemoryEntry) -> MemoryResponse:
    """Convert a SQLAlchemy MemoryEntry to a MemoryResponse schema."""
    return MemoryResponse(
        id=entry.id,
        venture_id=entry.venture_id,
        agent_id=entry.agent_id,
        memory_tier=entry.memory_tier,
        content=entry.content,
        summary=entry.summary,
        importance=entry.importance,
        access_count=entry.access_count,
        metadata=entry.metadata_,
        created_at=entry.created_at,
        last_accessed_at=entry.last_accessed_at,
    )


class MemoryEngine:
    """Multi-tier memory system for agent intelligence.

    Manages working, episodic, semantic, and procedural memories
    with importance scoring, access tracking, and context building.
    """

    def __init__(self) -> None:
        self._tracer = get_tracer()
        self._event_bus = get_event_bus()

    async def store(self, venture_id: str, data: MemoryStore) -> MemoryResponse:
        """Store a new memory entry.

        Args:
            venture_id: The venture this memory belongs to.
            data: Memory store request with tier, content, etc.

        Returns:
            The created memory entry as a response.
        """
        async with self._tracer.span("memory_engine", "store", input_data={"tier": data.tier}):
            if data.tier not in VALID_TIERS:
                raise ValueError(f"Invalid memory tier: {data.tier}. Must be one of {VALID_TIERS}")

            entry = MemoryEntry(
                venture_id=venture_id,
                agent_id=data.agent_id,
                memory_tier=data.tier,
                content=data.content,
                importance=data.importance,
                metadata_=data.metadata,
            )

            async with get_session(venture_id) as session:
                session.add(entry)
                await session.flush()
                await session.refresh(entry)
                response = _entry_to_response(entry)

            await self._event_bus.publish(
                event_type="memory.stored",
                source_module="memory_engine",
                payload={
                    "memory_id": response.id,
                    "tier": data.tier,
                    "agent_id": data.agent_id,
                    "importance": data.importance,
                },
                venture_id=venture_id,
            )

            logger.info(
                "memory_stored",
                venture_id=venture_id,
                memory_id=response.id,
                tier=data.tier,
                agent_id=data.agent_id,
            )

            return response

    async def recall(self, venture_id: str, query: MemoryQuery) -> list[MemoryResponse]:
        """Retrieve memories matching the query criteria.

        Supports keyword search (ILIKE), tier filtering, agent filtering,
        and minimum importance thresholds. Updates access tracking on results.

        Args:
            venture_id: The venture to search within.
            query: Query parameters for filtering memories.

        Returns:
            List of matching memory entries.
        """
        async with self._tracer.span("memory_engine", "recall", input_data={"query": query.model_dump()}):
            async with get_session(venture_id) as session:
                stmt = (
                    select(MemoryEntry)
                    .where(MemoryEntry.venture_id == venture_id)
                    .where(MemoryEntry.deleted_at.is_(None))
                    .where(MemoryEntry.importance >= query.min_importance)
                )

                if query.agent_id is not None:
                    stmt = stmt.where(MemoryEntry.agent_id == query.agent_id)

                if query.tier is not None:
                    if query.tier not in VALID_TIERS:
                        raise ValueError(f"Invalid memory tier: {query.tier}")
                    stmt = stmt.where(MemoryEntry.memory_tier == query.tier)

                if query.query is not None:
                    stmt = stmt.where(MemoryEntry.content.ilike(f"%{query.query}%"))

                stmt = stmt.order_by(MemoryEntry.created_at.desc()).limit(query.limit)

                result = await session.execute(stmt)
                entries = result.scalars().all()

                # Update access tracking
                now = datetime.now(UTC)
                if entries:
                    entry_ids = [e.id for e in entries]
                    await session.execute(
                        update(MemoryEntry)
                        .where(MemoryEntry.id.in_(entry_ids))
                        .values(
                            access_count=MemoryEntry.access_count + 1,
                            last_accessed_at=now,
                        )
                    )

                responses = [_entry_to_response(e) for e in entries]

            await self._event_bus.publish(
                event_type="memory.recalled",
                source_module="memory_engine",
                payload={
                    "query": query.model_dump(),
                    "result_count": len(responses),
                },
                venture_id=venture_id,
            )

            logger.info(
                "memory_recalled",
                venture_id=venture_id,
                result_count=len(responses),
                tier=query.tier,
                agent_id=query.agent_id,
            )

            return responses

    async def get_context(
        self, venture_id: str, agent_id: str, token_budget: int = 4000
    ) -> MemoryContext:
        """Build a context window from all memory tiers for an agent.

        Priority order: working > episodic > semantic > procedural.
        Fills until token_budget is reached.

        Args:
            venture_id: The venture context.
            agent_id: The agent to build context for.
            token_budget: Maximum estimated tokens to include.

        Returns:
            MemoryContext with entries from each tier.
        """
        async with self._tracer.span(
            "memory_engine", "get_context", input_data={"agent_id": agent_id, "token_budget": token_budget}
        ):
            context = MemoryContext()
            remaining_budget = token_budget

            async with get_session(venture_id) as session:
                # 1. Working memories — all of them, most recent first
                working_entries = await self._fetch_tier_entries(
                    session, venture_id, agent_id, "working", limit=50
                )
                for entry in working_entries:
                    tokens = _estimate_tokens(entry.content)
                    if tokens > remaining_budget:
                        break
                    context.working.append(_entry_to_response(entry))
                    remaining_budget -= tokens

                # 2. Episodic memories — sorted by last_accessed + importance
                if remaining_budget > 0:
                    episodic_entries = await self._fetch_tier_entries(
                        session, venture_id, agent_id, "episodic", limit=20,
                        order_by_importance=True,
                    )
                    for entry in episodic_entries:
                        tokens = _estimate_tokens(entry.content)
                        if tokens > remaining_budget:
                            break
                        context.episodic.append(_entry_to_response(entry))
                        remaining_budget -= tokens

                # 3. Semantic memories — highest importance
                if remaining_budget > 0:
                    semantic_entries = await self._fetch_tier_entries(
                        session, venture_id, agent_id, "semantic", limit=20,
                        order_by_importance=True,
                    )
                    for entry in semantic_entries:
                        tokens = _estimate_tokens(entry.content)
                        if tokens > remaining_budget:
                            break
                        context.semantic.append(_entry_to_response(entry))
                        remaining_budget -= tokens

                # 4. Procedural memories — relevant patterns
                if remaining_budget > 0:
                    procedural_entries = await self._fetch_tier_entries(
                        session, venture_id, agent_id, "procedural", limit=10,
                        order_by_importance=True,
                    )
                    for entry in procedural_entries:
                        tokens = _estimate_tokens(entry.content)
                        if tokens > remaining_budget:
                            break
                        context.procedural.append(_entry_to_response(entry))
                        remaining_budget -= tokens

            context.total_tokens_estimate = token_budget - remaining_budget

            logger.info(
                "memory_context_built",
                venture_id=venture_id,
                agent_id=agent_id,
                working_count=len(context.working),
                episodic_count=len(context.episodic),
                semantic_count=len(context.semantic),
                procedural_count=len(context.procedural),
                tokens_used=context.total_tokens_estimate,
            )

            return context

    async def consolidate(self, venture_id: str, request: ConsolidateRequest) -> int:
        """Compress old episodic memories into summaries.

        Memories older than max_age_hours that don't already have a summary
        get their content truncated to first 200 chars as a summary.

        Args:
            venture_id: The venture context.
            request: Consolidation parameters.

        Returns:
            Number of memories consolidated.
        """
        async with self._tracer.span("memory_engine", "consolidate"):
            cutoff = datetime.now(UTC) - timedelta(hours=request.max_age_hours)
            consolidated_count = 0

            async with get_session(venture_id) as session:
                stmt = (
                    select(MemoryEntry)
                    .where(MemoryEntry.venture_id == venture_id)
                    .where(MemoryEntry.memory_tier == "episodic")
                    .where(MemoryEntry.deleted_at.is_(None))
                    .where(MemoryEntry.summary.is_(None))
                    .where(MemoryEntry.created_at < cutoff)
                )

                if request.agent_id is not None:
                    stmt = stmt.where(MemoryEntry.agent_id == request.agent_id)

                result = await session.execute(stmt)
                entries = result.scalars().all()

                for entry in entries:
                    # Simple consolidation: truncate content to first 200 chars as summary
                    entry.summary = entry.content[:200]
                    consolidated_count += 1

            await self._event_bus.publish(
                event_type="memory.consolidated",
                source_module="memory_engine",
                payload={
                    "consolidated_count": consolidated_count,
                    "max_age_hours": request.max_age_hours,
                    "agent_id": request.agent_id,
                },
                venture_id=venture_id,
            )

            logger.info(
                "memory_consolidated",
                venture_id=venture_id,
                consolidated_count=consolidated_count,
                max_age_hours=request.max_age_hours,
            )

            return consolidated_count

    async def forget(self, venture_id: str, memory_id: str) -> None:
        """Soft-delete a memory entry.

        Args:
            venture_id: The venture context.
            memory_id: The ID of the memory to forget.
        """
        async with self._tracer.span("memory_engine", "forget", input_data={"memory_id": memory_id}):
            async with get_session(venture_id) as session:
                stmt = (
                    select(MemoryEntry)
                    .where(MemoryEntry.id == memory_id)
                    .where(MemoryEntry.venture_id == venture_id)
                    .where(MemoryEntry.deleted_at.is_(None))
                )
                result = await session.execute(stmt)
                entry = result.scalar_one_or_none()

                if entry is None:
                    raise ValueError(f"Memory entry not found: {memory_id}")

                entry.deleted_at = datetime.now(UTC)

            await self._event_bus.publish(
                event_type="memory.forgotten",
                source_module="memory_engine",
                payload={"memory_id": memory_id},
                venture_id=venture_id,
            )

            logger.info(
                "memory_forgotten",
                venture_id=venture_id,
                memory_id=memory_id,
            )

    async def update_importance(
        self, venture_id: str, memory_id: str, importance: float
    ) -> MemoryResponse:
        """Update the importance score of a memory entry.

        Args:
            venture_id: The venture context.
            memory_id: The ID of the memory to update.
            importance: New importance score (0.0 to 1.0).

        Returns:
            The updated memory entry.
        """
        async with self._tracer.span("memory_engine", "update_importance"):
            if not 0.0 <= importance <= 1.0:
                raise ValueError(f"Importance must be between 0.0 and 1.0, got {importance}")

            async with get_session(venture_id) as session:
                stmt = (
                    select(MemoryEntry)
                    .where(MemoryEntry.id == memory_id)
                    .where(MemoryEntry.venture_id == venture_id)
                    .where(MemoryEntry.deleted_at.is_(None))
                )
                result = await session.execute(stmt)
                entry = result.scalar_one_or_none()

                if entry is None:
                    raise ValueError(f"Memory entry not found: {memory_id}")

                entry.importance = importance
                await session.flush()
                await session.refresh(entry)
                response = _entry_to_response(entry)

            logger.info(
                "memory_importance_updated",
                venture_id=venture_id,
                memory_id=memory_id,
                importance=importance,
            )

            return response

    async def get_agent_memories(
        self, venture_id: str, agent_id: str, tier: str | None = None
    ) -> list[MemoryResponse]:
        """Get all memories for a specific agent, optionally filtered by tier.

        Args:
            venture_id: The venture context.
            agent_id: The agent whose memories to retrieve.
            tier: Optional tier filter.

        Returns:
            List of memory entries for the agent.
        """
        async with self._tracer.span("memory_engine", "get_agent_memories"):
            if tier is not None and tier not in VALID_TIERS:
                raise ValueError(f"Invalid memory tier: {tier}")

            async with get_session(venture_id) as session:
                stmt = (
                    select(MemoryEntry)
                    .where(MemoryEntry.venture_id == venture_id)
                    .where(MemoryEntry.agent_id == agent_id)
                    .where(MemoryEntry.deleted_at.is_(None))
                )

                if tier is not None:
                    stmt = stmt.where(MemoryEntry.memory_tier == tier)

                stmt = stmt.order_by(MemoryEntry.created_at.desc())

                result = await session.execute(stmt)
                entries = result.scalars().all()

            return [_entry_to_response(e) for e in entries]

    @staticmethod
    async def _fetch_tier_entries(
        session,
        venture_id: str,
        agent_id: str,
        tier: str,
        limit: int = 20,
        order_by_importance: bool = False,
    ) -> list[MemoryEntry]:
        """Fetch memory entries for a specific tier.

        Args:
            session: Active database session.
            venture_id: The venture context.
            agent_id: The agent whose memories to fetch.
            tier: The memory tier to query.
            limit: Maximum entries to return.
            order_by_importance: If True, sort by importance desc then created_at desc.

        Returns:
            List of MemoryEntry objects.
        """
        stmt = (
            select(MemoryEntry)
            .where(MemoryEntry.venture_id == venture_id)
            .where(MemoryEntry.agent_id == agent_id)
            .where(MemoryEntry.memory_tier == tier)
            .where(MemoryEntry.deleted_at.is_(None))
        )

        if order_by_importance:
            stmt = stmt.order_by(
                MemoryEntry.importance.desc(),
                MemoryEntry.created_at.desc(),
            )
        else:
            stmt = stmt.order_by(MemoryEntry.created_at.desc())

        stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        return list(result.scalars().all())
