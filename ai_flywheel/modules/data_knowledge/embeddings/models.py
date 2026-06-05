"""SQLAlchemy models for the Embedding Engine module.

EmbeddingCollection — a named collection with embedding configuration
EmbeddingDocument — a chunk of text with its embedding vector stored as JSONB
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class EmbeddingCollection(BaseModel, VentureScopedMixin):
    """A named collection of embedding documents with shared configuration."""

    __tablename__ = "embedding_collections"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, default="text-embedding-3-small"
    )
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False, default=1536)
    chunk_strategy: Mapped[str] = mapped_column(
        String(50), nullable=False, default="paragraph"
    )  # sentence, paragraph, fixed, semantic
    chunk_size: Mapped[int] = mapped_column(Integer, nullable=False, default=512)
    chunk_overlap: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )  # active, migrating, archived

    # Relationships
    documents: Mapped[list[EmbeddingDocument]] = relationship(
        "EmbeddingDocument", back_populates="collection", lazy="selectin"
    )


class EmbeddingDocument(BaseModel, VentureScopedMixin):
    """A single chunk of text with its embedding vector."""

    __tablename__ = "embedding_documents"

    collection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("embedding_collections.id"), nullable=False
    )
    source_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )  # links to ingestor DataSource
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    embedding_vector: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )  # list[float], pgvector in Phase 5

    # Relationships
    collection: Mapped[EmbeddingCollection] = relationship(
        "EmbeddingCollection", back_populates="documents"
    )
