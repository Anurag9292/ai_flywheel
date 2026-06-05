"""SQLAlchemy models for the Knowledge Graph Builder module.

KnowledgeGraph — a named graph with entity/relationship type registries
Entity — a node in the graph with type, properties, and confidence
Relationship — a directed edge between two entities
"""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class KnowledgeGraph(BaseModel, VentureScopedMixin):
    """A named knowledge graph containing entities and relationships."""

    __tablename__ = "knowledge_graphs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
    entity_types: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    relationship_types: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    entity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    relationship_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="building"
    )  # building, active, archived

    # Relationships
    entities: Mapped[list[Entity]] = relationship(
        "Entity", back_populates="graph", lazy="selectin"
    )
    relationships: Mapped[list[Relationship]] = relationship(
        "Relationship", back_populates="graph", lazy="selectin"
    )


class Entity(BaseModel, VentureScopedMixin):
    """A node in a knowledge graph with type, properties, and confidence."""

    __tablename__ = "knowledge_graph_entities"

    graph_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_graphs.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source_document_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, default=None
    )
    mentions: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    graph: Mapped[KnowledgeGraph] = relationship(
        "KnowledgeGraph", back_populates="entities"
    )


class Relationship(BaseModel, VentureScopedMixin):
    """A directed edge between two entities in a knowledge graph."""

    __tablename__ = "knowledge_graph_relationships"

    graph_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_graphs.id"), nullable=False
    )
    source_entity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_graph_entities.id"), nullable=False
    )
    target_entity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_graph_entities.id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source_document_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, default=None
    )

    # Relationships
    graph: Mapped[KnowledgeGraph] = relationship(
        "KnowledgeGraph", back_populates="relationships"
    )
    source_entity: Mapped[Entity] = relationship(
        "Entity", foreign_keys=[source_entity_id]
    )
    target_entity: Mapped[Entity] = relationship(
        "Entity", foreign_keys=[target_entity_id]
    )
