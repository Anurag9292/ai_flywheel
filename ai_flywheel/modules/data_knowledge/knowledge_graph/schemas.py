"""Pydantic schemas for the Knowledge Graph Builder module.

Request/response models for graph creation, entity extraction,
graph querying, and entity merging operations.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GraphCreate(BaseModel):
    """Request to create a new knowledge graph."""

    name: str
    description: str = ""


class GraphResponse(BaseModel):
    """Response containing knowledge graph details."""

    id: str
    venture_id: str
    name: str
    description: str | None
    entity_types: list[str]
    relationship_types: list[str]
    entity_count: int
    relationship_count: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EntityResult(BaseModel):
    """A single entity extracted or retrieved from the graph."""

    id: str
    entity_type: str
    name: str
    properties: dict = Field(default_factory=dict)
    confidence: float


class RelationshipResult(BaseModel):
    """A single relationship extracted or retrieved from the graph."""

    id: str
    source_entity: str
    target_entity: str
    relationship_type: str
    properties: dict = Field(default_factory=dict)
    confidence: float


class ExtractRequest(BaseModel):
    """Request to extract entities and relationships from text."""

    graph_id: str
    text: str
    source_document_id: str | None = None


class ExtractResult(BaseModel):
    """Result of an entity/relationship extraction operation."""

    graph_id: str
    entities_extracted: list[EntityResult] = Field(default_factory=list)
    relationships_extracted: list[RelationshipResult] = Field(default_factory=list)
    entity_types_discovered: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    """Request to query the knowledge graph."""

    graph_id: str
    query: str
    max_hops: int = 2


class QueryResult(BaseModel):
    """Result of a knowledge graph query."""

    entities: list[EntityResult] = Field(default_factory=list)
    relationships: list[RelationshipResult] = Field(default_factory=list)
    subgraph_summary: str = ""


class EntityMergeRequest(BaseModel):
    """Request to merge duplicate entities into one."""

    graph_id: str
    entity_ids: list[str]
    primary_name: str
