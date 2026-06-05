# ruff: noqa: E501
"""Knowledge Graph Builder service — extracts entities and relationships from text.

Uses LLM-powered extraction with entity resolution, graph traversal,
and entity merging capabilities.
"""

from __future__ import annotations

import json
import re
from typing import Any

import structlog
from sqlalchemy import or_, select, update

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.llm import generate
from ai_flywheel.core.traces import get_tracer

from .models import Entity, KnowledgeGraph, Relationship
from .schemas import (
    EntityMergeRequest,
    EntityResult,
    ExtractRequest,
    ExtractResult,
    GraphCreate,
    GraphResponse,
    QueryRequest,
    QueryResult,
    RelationshipResult,
)

logger = structlog.get_logger()

# LLM extraction prompt
EXTRACTION_SYSTEM_PROMPT = """You are a knowledge graph extraction engine. Given text, extract entities and relationships.

Output ONLY valid JSON with this exact structure:
{
  "entities": [
    {
      "entity_type": "string (e.g. Person, Organization, Technology, Concept, Location, Event)",
      "name": "string (canonical name)",
      "properties": {"key": "value pairs of notable attributes"}
    }
  ],
  "relationships": [
    {
      "source": "exact entity name from entities list",
      "target": "exact entity name from entities list",
      "relationship_type": "string (e.g. WORKS_FOR, LOCATED_IN, USES, FOUNDED, PART_OF)",
      "properties": {"key": "value pairs"}
    }
  ]
}

Rules:
- Extract ALL meaningful entities and relationships from the text
- Use consistent entity types (capitalize first letter)
- Use UPPER_SNAKE_CASE for relationship types
- Entity names should be the most complete/canonical form mentioned
- Include relevant properties when available
- Every relationship must reference entities that exist in the entities list
- Do not include duplicate entities (same name and type)"""

EXTRACTION_USER_PROMPT = """Extract entities and relationships from this text.

Known entity types in this graph: {entity_types}
Known relationship types in this graph: {relationship_types}

You may discover new entity/relationship types not listed above.

Text:
---
{text}
---

Return the JSON extraction:"""

QUERY_SYSTEM_PROMPT = """You are a knowledge graph query interpreter. Given a natural language query and a subgraph of entities and relationships, provide a concise summary that answers the query based on the available graph data.

Be factual and only reference information present in the provided subgraph."""

QUERY_USER_PROMPT = """Query: {query}

Subgraph data:
Entities: {entities}
Relationships: {relationships}

Provide a concise summary answering the query based on this subgraph:"""


def _similarity(a: str, b: str) -> float:
    """Simple case-insensitive containment/overlap similarity."""
    a_lower, b_lower = a.lower(), b.lower()
    if a_lower == b_lower:
        return 1.0
    if a_lower in b_lower or b_lower in a_lower:
        return 0.9
    # Word overlap
    words_a = set(a_lower.split())
    words_b = set(b_lower.split())
    if not words_a or not words_b:
        return 0.0
    overlap = len(words_a & words_b)
    return overlap / max(len(words_a), len(words_b))


def _parse_llm_json(content: str) -> dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code fences."""
    # Strip markdown code fences if present
    content = content.strip()
    if content.startswith("```"):
        # Remove opening fence (with optional language tag)
        content = re.sub(r"^```(?:json)?\s*\n?", "", content)
        # Remove closing fence
        content = re.sub(r"\n?```\s*$", "", content)

    return json.loads(content)


class KnowledgeGraphBuilder:
    """Service for building and querying knowledge graphs via LLM extraction."""

    def __init__(self) -> None:
        self._tracer = get_tracer()
        self._event_bus = get_event_bus()

    async def create_graph(
        self, venture_id: str, data: GraphCreate
    ) -> GraphResponse:
        """Create a new knowledge graph."""
        async with self._tracer.span(
            "knowledge_graph", "create_graph", input_data={"name": data.name}
        ) as span:
            async with get_session(venture_id) as session:
                graph = KnowledgeGraph(
                    venture_id=venture_id,
                    name=data.name,
                    description=data.description,
                    entity_types=[],
                    relationship_types=[],
                    entity_count=0,
                    relationship_count=0,
                    status="building",
                )
                session.add(graph)
                await session.flush()

                response = GraphResponse.model_validate(graph)

            span.output_data = {"graph_id": response.id}

        await self._event_bus.publish(
            event_type="kg.graph.created",
            source_module="knowledge_graph",
            payload={"graph_id": response.id, "name": data.name},
            venture_id=venture_id,
        )

        logger.info(
            "knowledge_graph_created",
            graph_id=response.id,
            name=data.name,
            venture_id=venture_id,
        )
        return response

    async def get_graph(self, venture_id: str, graph_id: str) -> GraphResponse:
        """Get a knowledge graph by ID."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(KnowledgeGraph).where(
                    KnowledgeGraph.id == graph_id,
                    KnowledgeGraph.venture_id == venture_id,
                    KnowledgeGraph.deleted_at.is_(None),
                )
            )
            graph = result.scalar_one_or_none()
            if graph is None:
                raise ValueError(
                    f"Graph {graph_id} not found for venture {venture_id}"
                )
            return GraphResponse.model_validate(graph)

    async def list_graphs(self, venture_id: str) -> list[GraphResponse]:
        """List all knowledge graphs for a venture."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(KnowledgeGraph).where(
                    KnowledgeGraph.venture_id == venture_id,
                    KnowledgeGraph.deleted_at.is_(None),
                )
            )
            graphs = result.scalars().all()
            return [GraphResponse.model_validate(g) for g in graphs]

    async def extract(
        self, venture_id: str, request: ExtractRequest
    ) -> ExtractResult:
        """Extract entities and relationships from text using LLM.

        1. Sends text to LLM for structured extraction
        2. Parses the JSON response
        3. Resolves entities against existing graph (fuzzy matching)
        4. Stores new entities and relationships
        5. Updates graph counters and type lists
        """
        async with self._tracer.span(
            "knowledge_graph",
            "extract",
            input_data={
                "graph_id": request.graph_id,
                "text_length": len(request.text),
            },
        ) as span:
            # Get current graph state for context
            graph_response = await self.get_graph(venture_id, request.graph_id)

            # Call LLM for extraction
            messages = [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": EXTRACTION_USER_PROMPT.format(
                        entity_types=", ".join(graph_response.entity_types) or "none yet",
                        relationship_types=", ".join(graph_response.relationship_types) or "none yet",
                        text=request.text,
                    ),
                },
            ]

            llm_response = await generate(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.3,
                venture_id=venture_id,
                module_name="knowledge_graph",
                metadata={"operation": "extract", "graph_id": request.graph_id},
            )

            # Parse the LLM JSON response
            try:
                extraction = _parse_llm_json(llm_response.content)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    "extraction_json_parse_failed",
                    error=str(e),
                    content_preview=llm_response.content[:200],
                    venture_id=venture_id,
                )
                return ExtractResult(
                    graph_id=request.graph_id,
                    entities_extracted=[],
                    relationships_extracted=[],
                    entity_types_discovered=[],
                )

            raw_entities = extraction.get("entities", [])
            raw_relationships = extraction.get("relationships", [])

            # Load existing entities for resolution
            async with get_session(venture_id) as session:
                existing_result = await session.execute(
                    select(Entity).where(
                        Entity.graph_id == request.graph_id,
                        Entity.venture_id == venture_id,
                        Entity.deleted_at.is_(None),
                    )
                )
                existing_entities = list(existing_result.scalars().all())

            # Resolve and store entities
            entity_results: list[EntityResult] = []
            entity_name_to_id: dict[str, str] = {}
            new_entity_types: set[str] = set()
            new_relationship_types: set[str] = set()

            async with get_session(venture_id) as session:
                for raw_entity in raw_entities:
                    entity_type = raw_entity.get("entity_type", "Unknown")
                    entity_name = raw_entity.get("name", "")
                    entity_props = raw_entity.get("properties", {})

                    if not entity_name:
                        continue

                    # Track new entity types
                    if entity_type not in graph_response.entity_types:
                        new_entity_types.add(entity_type)

                    # Resolve against existing entities
                    resolved_entity = self._resolve_entity(
                        entity_name, entity_type, existing_entities
                    )

                    if resolved_entity is not None:
                        # Update existing entity — increment mentions, merge props
                        resolved_entity.mentions += 1
                        merged_props = {**resolved_entity.properties, **entity_props}
                        resolved_entity.properties = merged_props
                        session.add(resolved_entity)
                        await session.flush()

                        entity_name_to_id[entity_name] = resolved_entity.id
                        entity_results.append(
                            EntityResult(
                                id=resolved_entity.id,
                                entity_type=resolved_entity.entity_type,
                                name=resolved_entity.name,
                                properties=merged_props,
                                confidence=resolved_entity.confidence,
                            )
                        )
                    else:
                        # Create new entity
                        new_entity = Entity(
                            venture_id=venture_id,
                            graph_id=request.graph_id,
                            entity_type=entity_type,
                            name=entity_name,
                            properties=entity_props,
                            confidence=0.85,
                            source_document_id=request.source_document_id,
                            mentions=1,
                        )
                        session.add(new_entity)
                        await session.flush()

                        existing_entities.append(new_entity)
                        entity_name_to_id[entity_name] = new_entity.id
                        entity_results.append(
                            EntityResult(
                                id=new_entity.id,
                                entity_type=entity_type,
                                name=entity_name,
                                properties=entity_props,
                                confidence=0.85,
                            )
                        )

                # Store relationships
                relationship_results: list[RelationshipResult] = []
                for raw_rel in raw_relationships:
                    source_name = raw_rel.get("source", "")
                    target_name = raw_rel.get("target", "")
                    rel_type = raw_rel.get("relationship_type", "RELATED_TO")
                    rel_props = raw_rel.get("properties", {})

                    source_id = entity_name_to_id.get(source_name)
                    target_id = entity_name_to_id.get(target_name)

                    if not source_id or not target_id:
                        # Try fuzzy match against known entity names
                        if not source_id:
                            source_id = self._fuzzy_resolve_name(
                                source_name, entity_name_to_id
                            )
                        if not target_id:
                            target_id = self._fuzzy_resolve_name(
                                target_name, entity_name_to_id
                            )

                    if not source_id or not target_id:
                        logger.debug(
                            "relationship_skipped_missing_entity",
                            source=source_name,
                            target=target_name,
                        )
                        continue

                    # Track new relationship types
                    if rel_type not in graph_response.relationship_types:
                        new_relationship_types.add(rel_type)

                    new_rel = Relationship(
                        venture_id=venture_id,
                        graph_id=request.graph_id,
                        source_entity_id=source_id,
                        target_entity_id=target_id,
                        relationship_type=rel_type,
                        properties=rel_props,
                        confidence=0.8,
                        source_document_id=request.source_document_id,
                    )
                    session.add(new_rel)
                    await session.flush()

                    relationship_results.append(
                        RelationshipResult(
                            id=new_rel.id,
                            source_entity=source_name,
                            target_entity=target_name,
                            relationship_type=rel_type,
                            properties=rel_props,
                            confidence=0.8,
                        )
                    )

                # Update graph counters and type lists
                updated_entity_types = list(
                    set(graph_response.entity_types) | new_entity_types
                )
                updated_relationship_types = list(
                    set(graph_response.relationship_types) | new_relationship_types
                )

                await session.execute(
                    update(KnowledgeGraph)
                    .where(KnowledgeGraph.id == request.graph_id)
                    .values(
                        entity_count=KnowledgeGraph.entity_count + len(
                            [e for e in entity_results if e.confidence == 0.85]
                        ),
                        relationship_count=KnowledgeGraph.relationship_count + len(
                            relationship_results
                        ),
                        entity_types=updated_entity_types,
                        relationship_types=updated_relationship_types,
                        status="active",
                    )
                )

            span.set_cost(
                cost_usd=llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )
            span.output_data = {
                "entities_extracted": len(entity_results),
                "relationships_extracted": len(relationship_results),
                "new_entity_types": list(new_entity_types),
            }

        await self._event_bus.publish(
            event_type="kg.extraction.completed",
            source_module="knowledge_graph",
            payload={
                "graph_id": request.graph_id,
                "entities_extracted": len(entity_results),
                "relationships_extracted": len(relationship_results),
                "entity_types_discovered": list(new_entity_types),
                "cost_usd": llm_response.cost_usd,
            },
            venture_id=venture_id,
        )

        logger.info(
            "knowledge_graph_extraction_completed",
            graph_id=request.graph_id,
            entities_extracted=len(entity_results),
            relationships_extracted=len(relationship_results),
            new_entity_types=list(new_entity_types),
            venture_id=venture_id,
        )

        return ExtractResult(
            graph_id=request.graph_id,
            entities_extracted=entity_results,
            relationships_extracted=relationship_results,
            entity_types_discovered=list(new_entity_types),
        )

    async def query(
        self, venture_id: str, request: QueryRequest
    ) -> QueryResult:
        """Query the knowledge graph by traversing from query-relevant entities.

        Finds entities matching the query, then traverses up to max_hops
        to build a relevant subgraph. Uses LLM to summarize findings.
        """
        async with self._tracer.span(
            "knowledge_graph",
            "query",
            input_data={"graph_id": request.graph_id, "max_hops": request.max_hops},
        ) as span:
            # Find entities relevant to the query (simple keyword matching)
            query_words = set(request.query.lower().split())

            async with get_session(venture_id) as session:
                # Get all entities in the graph
                entity_result = await session.execute(
                    select(Entity).where(
                        Entity.graph_id == request.graph_id,
                        Entity.venture_id == venture_id,
                        Entity.deleted_at.is_(None),
                    )
                )
                all_entities = list(entity_result.scalars().all())

                # Score entities by relevance to query
                scored_entities: list[tuple[Entity, float]] = []
                for entity in all_entities:
                    entity_words = set(entity.name.lower().split())
                    overlap = len(query_words & entity_words)
                    if overlap > 0:
                        score = overlap / max(len(query_words), len(entity_words))
                        scored_entities.append((entity, score))

                # Also check if query words appear in entity type or properties
                for entity in all_entities:
                    if any(w in entity.entity_type.lower() for w in query_words):
                        if not any(e.id == entity.id for e, _ in scored_entities):
                            scored_entities.append((entity, 0.5))

                # Sort by score and take top seed entities
                scored_entities.sort(key=lambda x: x[1], reverse=True)
                seed_entities = [e for e, _ in scored_entities[:10]]

                if not seed_entities:
                    return QueryResult(
                        entities=[],
                        relationships=[],
                        subgraph_summary="No entities found matching the query.",
                    )

                # Traverse graph from seed entities up to max_hops
                visited_entity_ids: set[str] = set()
                frontier_ids: set[str] = {e.id for e in seed_entities}
                collected_relationships: list[Relationship] = []

                for _hop in range(request.max_hops):
                    if not frontier_ids:
                        break

                    visited_entity_ids.update(frontier_ids)

                    # Find relationships connected to frontier
                    rel_result = await session.execute(
                        select(Relationship).where(
                            Relationship.graph_id == request.graph_id,
                            Relationship.venture_id == venture_id,
                            Relationship.deleted_at.is_(None),
                            or_(
                                Relationship.source_entity_id.in_(frontier_ids),
                                Relationship.target_entity_id.in_(frontier_ids),
                            ),
                        )
                    )
                    hop_relationships = list(rel_result.scalars().all())
                    collected_relationships.extend(hop_relationships)

                    # Discover new entity IDs for next hop
                    next_frontier: set[str] = set()
                    for rel in hop_relationships:
                        if rel.source_entity_id not in visited_entity_ids:
                            next_frontier.add(rel.source_entity_id)
                        if rel.target_entity_id not in visited_entity_ids:
                            next_frontier.add(rel.target_entity_id)

                    frontier_ids = next_frontier

                # Collect all entities in the subgraph
                visited_entity_ids.update(frontier_ids)
                subgraph_entities = [
                    e for e in all_entities if e.id in visited_entity_ids
                ]

            # Build result entities and relationships
            entity_id_to_name: dict[str, str] = {
                e.id: e.name for e in subgraph_entities
            }

            result_entities = [
                EntityResult(
                    id=e.id,
                    entity_type=e.entity_type,
                    name=e.name,
                    properties=e.properties,
                    confidence=e.confidence,
                )
                for e in subgraph_entities
            ]

            # Deduplicate relationships
            seen_rel_ids: set[str] = set()
            result_relationships: list[RelationshipResult] = []
            for rel in collected_relationships:
                if rel.id in seen_rel_ids:
                    continue
                seen_rel_ids.add(rel.id)
                result_relationships.append(
                    RelationshipResult(
                        id=rel.id,
                        source_entity=entity_id_to_name.get(
                            rel.source_entity_id, rel.source_entity_id
                        ),
                        target_entity=entity_id_to_name.get(
                            rel.target_entity_id, rel.target_entity_id
                        ),
                        relationship_type=rel.relationship_type,
                        properties=rel.properties,
                        confidence=rel.confidence,
                    )
                )

            # Generate summary using LLM
            entities_desc = [
                f"{e.name} ({e.entity_type})" for e in subgraph_entities[:20]
            ]
            rels_desc = [
                f"{entity_id_to_name.get(r.source_entity_id, '?')} "
                f"-[{r.relationship_type}]-> "
                f"{entity_id_to_name.get(r.target_entity_id, '?')}"
                for r in collected_relationships[:20]
            ]

            summary_response = await generate(
                messages=[
                    {"role": "system", "content": QUERY_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": QUERY_USER_PROMPT.format(
                            query=request.query,
                            entities=", ".join(entities_desc) or "none",
                            relationships="; ".join(rels_desc) or "none",
                        ),
                    },
                ],
                model="gpt-4o-mini",
                temperature=0.3,
                venture_id=venture_id,
                module_name="knowledge_graph",
                metadata={"operation": "query_summary", "graph_id": request.graph_id},
            )

            span.output_data = {
                "entities_found": len(result_entities),
                "relationships_found": len(result_relationships),
            }

        return QueryResult(
            entities=result_entities,
            relationships=result_relationships,
            subgraph_summary=summary_response.content,
        )

    async def merge_entities(
        self, venture_id: str, request: EntityMergeRequest
    ) -> EntityResult:
        """Merge duplicate entities into a single entity.

        Keeps the first entity as primary, merges properties from all others,
        redirects relationships, and soft-deletes the duplicates.
        """
        async with self._tracer.span(
            "knowledge_graph",
            "merge_entities",
            input_data={
                "graph_id": request.graph_id,
                "entity_count": len(request.entity_ids),
            },
        ) as span:
            from datetime import UTC, datetime

            async with get_session(venture_id) as session:
                # Load all entities to merge
                entity_result = await session.execute(
                    select(Entity).where(
                        Entity.id.in_(request.entity_ids),
                        Entity.graph_id == request.graph_id,
                        Entity.venture_id == venture_id,
                        Entity.deleted_at.is_(None),
                    )
                )
                entities = list(entity_result.scalars().all())

                if len(entities) < 2:
                    raise ValueError(
                        "At least 2 valid entities are required for merging"
                    )

                # Use first entity as primary
                primary = entities[0]
                others = entities[1:]

                # Merge properties and mentions
                merged_properties = dict(primary.properties)
                total_mentions = primary.mentions
                for other in others:
                    merged_properties.update(other.properties)
                    total_mentions += other.mentions

                # Update primary entity
                primary.name = request.primary_name
                primary.properties = merged_properties
                primary.mentions = total_mentions
                primary.confidence = min(
                    1.0, primary.confidence + 0.05 * len(others)
                )
                session.add(primary)

                # Redirect relationships from other entities to primary
                other_ids = [e.id for e in others]

                await session.execute(
                    update(Relationship)
                    .where(
                        Relationship.source_entity_id.in_(other_ids),
                        Relationship.deleted_at.is_(None),
                    )
                    .values(source_entity_id=primary.id)
                )

                await session.execute(
                    update(Relationship)
                    .where(
                        Relationship.target_entity_id.in_(other_ids),
                        Relationship.deleted_at.is_(None),
                    )
                    .values(target_entity_id=primary.id)
                )

                # Soft-delete the merged entities
                now = datetime.now(UTC)
                for other in others:
                    other.deleted_at = now
                    session.add(other)

                # Update graph entity count
                await session.execute(
                    update(KnowledgeGraph)
                    .where(KnowledgeGraph.id == request.graph_id)
                    .values(
                        entity_count=KnowledgeGraph.entity_count - len(others)
                    )
                )

                await session.flush()

                result = EntityResult(
                    id=primary.id,
                    entity_type=primary.entity_type,
                    name=primary.name,
                    properties=primary.properties,
                    confidence=primary.confidence,
                )

            span.output_data = {
                "primary_id": primary.id,
                "merged_count": len(others),
            }

        await self._event_bus.publish(
            event_type="kg.entities.merged",
            source_module="knowledge_graph",
            payload={
                "graph_id": request.graph_id,
                "primary_entity_id": primary.id,
                "merged_entity_ids": other_ids,
                "primary_name": request.primary_name,
            },
            venture_id=venture_id,
        )

        logger.info(
            "knowledge_graph_entities_merged",
            graph_id=request.graph_id,
            primary_id=primary.id,
            merged_count=len(others),
            venture_id=venture_id,
        )

        return result

    async def get_entity(
        self, venture_id: str, graph_id: str, entity_id: str
    ) -> EntityResult:
        """Get a single entity by ID."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Entity).where(
                    Entity.id == entity_id,
                    Entity.graph_id == graph_id,
                    Entity.venture_id == venture_id,
                    Entity.deleted_at.is_(None),
                )
            )
            entity = result.scalar_one_or_none()
            if entity is None:
                raise ValueError(
                    f"Entity {entity_id} not found in graph {graph_id}"
                )
            return EntityResult(
                id=entity.id,
                entity_type=entity.entity_type,
                name=entity.name,
                properties=entity.properties,
                confidence=entity.confidence,
            )

    async def get_neighbors(
        self, venture_id: str, graph_id: str, entity_id: str
    ) -> QueryResult:
        """Get directly connected entities (1-hop neighbors)."""
        async with self._tracer.span(
            "knowledge_graph",
            "get_neighbors",
            input_data={"graph_id": graph_id, "entity_id": entity_id},
        ):
            async with get_session(venture_id) as session:
                # Get relationships where entity is source or target
                rel_result = await session.execute(
                    select(Relationship).where(
                        Relationship.graph_id == graph_id,
                        Relationship.venture_id == venture_id,
                        Relationship.deleted_at.is_(None),
                        or_(
                            Relationship.source_entity_id == entity_id,
                            Relationship.target_entity_id == entity_id,
                        ),
                    )
                )
                relationships = list(rel_result.scalars().all())

                # Collect neighbor entity IDs
                neighbor_ids: set[str] = set()
                for rel in relationships:
                    if rel.source_entity_id != entity_id:
                        neighbor_ids.add(rel.source_entity_id)
                    if rel.target_entity_id != entity_id:
                        neighbor_ids.add(rel.target_entity_id)

                # Include the queried entity itself
                all_entity_ids = neighbor_ids | {entity_id}

                # Load neighbor entities
                entity_result = await session.execute(
                    select(Entity).where(
                        Entity.id.in_(all_entity_ids),
                        Entity.graph_id == graph_id,
                        Entity.venture_id == venture_id,
                        Entity.deleted_at.is_(None),
                    )
                )
                entities = list(entity_result.scalars().all())

            # Build response
            entity_id_to_name = {e.id: e.name for e in entities}

            result_entities = [
                EntityResult(
                    id=e.id,
                    entity_type=e.entity_type,
                    name=e.name,
                    properties=e.properties,
                    confidence=e.confidence,
                )
                for e in entities
            ]

            result_relationships = [
                RelationshipResult(
                    id=rel.id,
                    source_entity=entity_id_to_name.get(
                        rel.source_entity_id, rel.source_entity_id
                    ),
                    target_entity=entity_id_to_name.get(
                        rel.target_entity_id, rel.target_entity_id
                    ),
                    relationship_type=rel.relationship_type,
                    properties=rel.properties,
                    confidence=rel.confidence,
                )
                for rel in relationships
            ]

            return QueryResult(
                entities=result_entities,
                relationships=result_relationships,
                subgraph_summary=f"Direct neighbors of entity {entity_id}: "
                f"{len(result_entities) - 1} connected entities via "
                f"{len(result_relationships)} relationships.",
            )

    def _resolve_entity(
        self, name: str, entity_type: str, existing_entities: list[Entity]
    ) -> Entity | None:
        """Resolve a new entity against existing entities using fuzzy matching.

        Returns the matching existing entity if similarity >= 0.9 and same type,
        or None if no match found.
        """
        best_match: Entity | None = None
        best_score: float = 0.0

        for existing in existing_entities:
            if existing.entity_type != entity_type:
                continue

            score = _similarity(name, existing.name)
            if score >= 0.9 and score > best_score:
                best_match = existing
                best_score = score

        return best_match

    def _fuzzy_resolve_name(
        self, name: str, entity_name_to_id: dict[str, str]
    ) -> str | None:
        """Try to fuzzy-match a name against known entity names."""
        best_id: str | None = None
        best_score: float = 0.0

        for known_name, entity_id in entity_name_to_id.items():
            score = _similarity(name, known_name)
            if score >= 0.9 and score > best_score:
                best_id = entity_id
                best_score = score

        return best_id
