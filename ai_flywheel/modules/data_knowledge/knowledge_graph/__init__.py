"""Knowledge Graph Builder — LLM-powered entity/relationship extraction and graph querying.

Phase 2, Module #17: Extracts entities and relationships from text using LLM,
resolves duplicates via fuzzy matching, stores in a queryable graph structure,
and supports multi-hop traversal queries with LLM-generated summaries.
"""

from ai_flywheel.modules.data_knowledge.knowledge_graph.models import (
    Entity,
    KnowledgeGraph,
    Relationship,
)
from ai_flywheel.modules.data_knowledge.knowledge_graph.schemas import (
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
from ai_flywheel.modules.data_knowledge.knowledge_graph.service import (
    KnowledgeGraphBuilder,
)

__all__ = [
    "Entity",
    "EntityMergeRequest",
    "EntityResult",
    "ExtractRequest",
    "ExtractResult",
    "GraphCreate",
    "GraphResponse",
    "KnowledgeGraph",
    "KnowledgeGraphBuilder",
    "QueryRequest",
    "QueryResult",
    "Relationship",
    "RelationshipResult",
]
