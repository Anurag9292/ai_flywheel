"""Embedding Engine — vector embedding generation, storage, and similarity search.

Phase 2, Module #16: Provides text chunking, embedding generation via OpenAI,
and cosine-similarity-based vector search. Stores embeddings as JSONB for now;
pgvector migration is a Phase 5 concern.
"""

from ai_flywheel.modules.data_knowledge.embeddings.chunking import chunk_text
from ai_flywheel.modules.data_knowledge.embeddings.models import (
    EmbeddingCollection,
    EmbeddingDocument,
)
from ai_flywheel.modules.data_knowledge.embeddings.schemas import (
    ChunkResult,
    CollectionCreate,
    CollectionResponse,
    EmbedRequest,
    EmbedResult,
    SearchHit,
    SearchRequest,
    SearchResult,
)
from ai_flywheel.modules.data_knowledge.embeddings.service import EmbeddingEngine

__all__ = [
    "EmbeddingCollection",
    "EmbeddingDocument",
    "CollectionCreate",
    "CollectionResponse",
    "EmbedRequest",
    "EmbedResult",
    "SearchRequest",
    "SearchResult",
    "SearchHit",
    "ChunkResult",
    "EmbeddingEngine",
    "chunk_text",
]
