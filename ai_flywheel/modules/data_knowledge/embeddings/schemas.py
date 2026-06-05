"""Pydantic schemas for the Embedding Engine module.

Request/response models for embedding operations.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    """Request to create a new embedding collection."""

    name: str
    model_name: str = "text-embedding-3-small"
    dimensions: int = 1536
    chunk_strategy: str = "paragraph"  # sentence, paragraph, fixed, semantic
    chunk_size: int = 512
    chunk_overlap: int = 50


class CollectionResponse(BaseModel):
    """Response containing embedding collection details."""

    id: str
    venture_id: str
    name: str
    model_name: str
    dimensions: int
    chunk_strategy: str
    chunk_size: int
    chunk_overlap: int
    document_count: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EmbedRequest(BaseModel):
    """Request to embed texts into a collection."""

    collection_id: str
    texts: list[str]
    metadata: list[dict] | None = None
    source_id: str | None = None


class EmbedResult(BaseModel):
    """Result of an embedding operation."""

    collection_id: str
    documents_created: int
    total_chunks: int
    model_used: str
    cost_usd: float


class SearchRequest(BaseModel):
    """Request to search for similar documents."""

    collection_id: str
    query: str
    top_k: int = 10
    filter_metadata: dict | None = None
    min_score: float = 0.0


class SearchHit(BaseModel):
    """A single search result with similarity score."""

    document_id: str
    content: str
    score: float
    metadata: dict
    chunk_index: int


class SearchResult(BaseModel):
    """Result of a similarity search."""

    results: list[SearchHit] = Field(default_factory=list)
    query_embedding_cost_usd: float


class ChunkResult(BaseModel):
    """Result of a text chunking operation."""

    chunks: list[str]
    strategy: str
    total_chunks: int
