"""Embedding Engine service — orchestrates embedding generation, storage, and search.

Handles collection CRUD, text chunking, OpenAI embedding API calls (via httpx),
document persistence, and cosine-similarity-based vector search.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from sqlalchemy import select, update

from ai_flywheel.core.config import settings
from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.traces import get_tracer

from .chunking import chunk_text as _chunk_text
from .models import EmbeddingCollection, EmbeddingDocument
from .schemas import (
    ChunkResult,
    CollectionCreate,
    CollectionResponse,
    EmbedRequest,
    EmbedResult,
    SearchHit,
    SearchRequest,
    SearchResult,
)

logger = structlog.get_logger()

# OpenAI embedding API constants
OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
MAX_BATCH_SIZE = 2048  # OpenAI allows up to 2048 texts per request

# Cost per 1K tokens for supported models
MODEL_COSTS: dict[str, float] = {
    "text-embedding-3-small": 0.00002,
    "text-embedding-3-large": 0.00013,
    "text-embedding-ada-002": 0.0001,
}


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def _estimate_tokens(text: str) -> int:
    """Estimate token count as len(text) / 4."""
    return max(1, len(text) // 4)


def _estimate_cost(texts: list[str], model_name: str) -> float:
    """Estimate cost for embedding a batch of texts."""
    total_tokens = sum(_estimate_tokens(t) for t in texts)
    cost_per_1k = MODEL_COSTS.get(model_name, 0.00002)
    return (total_tokens / 1000) * cost_per_1k


class EmbeddingEngine:
    """Service for embedding generation, storage, and similarity search."""

    def __init__(self) -> None:
        self._tracer = get_tracer()
        self._event_bus = get_event_bus()

    async def create_collection(
        self, venture_id: str, data: CollectionCreate
    ) -> CollectionResponse:
        """Create a new embedding collection."""
        async with self._tracer.span(
            "embedding_engine", "create_collection", input_data={"name": data.name}
        ) as span:
            async with get_session(venture_id) as session:
                collection = EmbeddingCollection(
                    venture_id=venture_id,
                    name=data.name,
                    model_name=data.model_name,
                    dimensions=data.dimensions,
                    chunk_strategy=data.chunk_strategy,
                    chunk_size=data.chunk_size,
                    chunk_overlap=data.chunk_overlap,
                    document_count=0,
                    status="active",
                )
                session.add(collection)
                await session.flush()

                response = CollectionResponse.model_validate(collection)

            span.output_data = {"collection_id": response.id}

        await self._event_bus.publish(
            event_type="embedding.collection.created",
            source_module="embedding_engine",
            payload={
                "collection_id": response.id,
                "name": data.name,
                "model_name": data.model_name,
                "dimensions": data.dimensions,
            },
            venture_id=venture_id,
        )

        logger.info(
            "embedding_collection_created",
            collection_id=response.id,
            name=data.name,
            venture_id=venture_id,
        )
        return response

    async def get_collection(
        self, venture_id: str, collection_id: str
    ) -> CollectionResponse:
        """Get an embedding collection by ID."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(EmbeddingCollection).where(
                    EmbeddingCollection.id == collection_id,
                    EmbeddingCollection.venture_id == venture_id,
                    EmbeddingCollection.deleted_at.is_(None),
                )
            )
            collection = result.scalar_one_or_none()
            if collection is None:
                raise ValueError(
                    f"Collection {collection_id} not found for venture {venture_id}"
                )
            return CollectionResponse.model_validate(collection)

    async def list_collections(self, venture_id: str) -> list[CollectionResponse]:
        """List all embedding collections for a venture."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(EmbeddingCollection).where(
                    EmbeddingCollection.venture_id == venture_id,
                    EmbeddingCollection.deleted_at.is_(None),
                )
            )
            collections = result.scalars().all()
            return [CollectionResponse.model_validate(c) for c in collections]

    async def embed(self, venture_id: str, request: EmbedRequest) -> EmbedResult:
        """Chunk texts, generate embeddings via OpenAI, and store documents.

        Handles batching for large inputs (OpenAI max 2048 texts per request).
        """
        async with self._tracer.span(
            "embedding_engine",
            "embed",
            input_data={
                "collection_id": request.collection_id,
                "text_count": len(request.texts),
            },
        ) as span:
            # Fetch collection config
            collection = await self.get_collection(venture_id, request.collection_id)

            # Chunk all texts
            all_chunks: list[str] = []
            chunk_metadata: list[dict[str, Any]] = []

            for i, text in enumerate(request.texts):
                chunks = _chunk_text(
                    text,
                    strategy=collection.chunk_strategy,
                    chunk_size=collection.chunk_size,
                    overlap=collection.chunk_overlap,
                )
                meta = (
                    request.metadata[i]
                    if request.metadata and i < len(request.metadata)
                    else {}
                )
                for chunk_idx, chunk in enumerate(chunks):
                    all_chunks.append(chunk)
                    chunk_metadata.append(
                        {**meta, "text_index": i, "chunk_index": chunk_idx}
                    )

            if not all_chunks:
                return EmbedResult(
                    collection_id=request.collection_id,
                    documents_created=0,
                    total_chunks=0,
                    model_used=collection.model_name,
                    cost_usd=0.0,
                )

            # Generate embeddings in batches
            all_embeddings: list[list[float]] = []
            total_cost = 0.0

            for batch_start in range(0, len(all_chunks), MAX_BATCH_SIZE):
                batch = all_chunks[batch_start : batch_start + MAX_BATCH_SIZE]
                embeddings, batch_cost = await self._generate_embeddings(
                    batch, collection.model_name
                )
                all_embeddings.extend(embeddings)
                total_cost += batch_cost

            # Store documents
            documents_created = 0
            async with get_session(venture_id) as session:
                for i, (chunk, embedding) in enumerate(
                    zip(all_chunks, all_embeddings)
                ):
                    doc = EmbeddingDocument(
                        venture_id=venture_id,
                        collection_id=request.collection_id,
                        source_id=request.source_id,
                        content=chunk,
                        chunk_index=chunk_metadata[i].get("chunk_index", i),
                        extra_metadata=chunk_metadata[i],
                        embedding_vector=embedding,
                    )
                    session.add(doc)
                    documents_created += 1

                # Update collection document count
                await session.execute(
                    update(EmbeddingCollection)
                    .where(EmbeddingCollection.id == request.collection_id)
                    .values(
                        document_count=EmbeddingCollection.document_count
                        + documents_created
                    )
                )

            span.set_cost(
                cost_usd=total_cost,
                tokens_input=sum(_estimate_tokens(c) for c in all_chunks),
                model=collection.model_name,
            )
            span.output_data = {
                "documents_created": documents_created,
                "total_chunks": len(all_chunks),
            }

        await self._event_bus.publish(
            event_type="embedding.documents.embedded",
            source_module="embedding_engine",
            payload={
                "collection_id": request.collection_id,
                "documents_created": documents_created,
                "total_chunks": len(all_chunks),
                "model_used": collection.model_name,
                "cost_usd": total_cost,
            },
            venture_id=venture_id,
        )

        logger.info(
            "embedding_documents_embedded",
            collection_id=request.collection_id,
            documents_created=documents_created,
            total_chunks=len(all_chunks),
            cost_usd=total_cost,
            venture_id=venture_id,
        )

        return EmbedResult(
            collection_id=request.collection_id,
            documents_created=documents_created,
            total_chunks=len(all_chunks),
            model_used=collection.model_name,
            cost_usd=total_cost,
        )

    async def search(self, venture_id: str, request: SearchRequest) -> SearchResult:
        """Embed query and compute cosine similarity against stored documents."""
        async with self._tracer.span(
            "embedding_engine",
            "search",
            input_data={
                "collection_id": request.collection_id,
                "top_k": request.top_k,
            },
        ) as span:
            # Get collection to know the model
            collection = await self.get_collection(venture_id, request.collection_id)

            # Embed the query
            query_embeddings, query_cost = await self._generate_embeddings(
                [request.query], collection.model_name
            )
            query_vector = query_embeddings[0]

            # Fetch all documents in the collection
            async with get_session(venture_id) as session:
                query = select(EmbeddingDocument).where(
                    EmbeddingDocument.collection_id == request.collection_id,
                    EmbeddingDocument.venture_id == venture_id,
                    EmbeddingDocument.deleted_at.is_(None),
                    EmbeddingDocument.embedding_vector.isnot(None),
                )
                result = await session.execute(query)
                documents = result.scalars().all()

            # Compute similarities
            scored_hits: list[SearchHit] = []
            for doc in documents:
                # Apply metadata filter if provided
                if request.filter_metadata:
                    if not _metadata_matches(doc.extra_metadata, request.filter_metadata):
                        continue

                score = cosine_similarity(query_vector, doc.embedding_vector)

                if score >= request.min_score:
                    scored_hits.append(
                        SearchHit(
                            document_id=doc.id,
                            content=doc.content,
                            score=score,
                            metadata=doc.extra_metadata or {},
                            chunk_index=doc.chunk_index,
                        )
                    )

            # Sort by score descending, take top_k
            scored_hits.sort(key=lambda h: h.score, reverse=True)
            top_results = scored_hits[: request.top_k]

            span.set_cost(
                cost_usd=query_cost,
                tokens_input=_estimate_tokens(request.query),
                model=collection.model_name,
            )
            span.output_data = {
                "results_count": len(top_results),
                "documents_scanned": len(documents),
            }

        await self._event_bus.publish(
            event_type="embedding.search.completed",
            source_module="embedding_engine",
            payload={
                "collection_id": request.collection_id,
                "results_count": len(top_results),
                "documents_scanned": len(documents),
                "query_cost_usd": query_cost,
            },
            venture_id=venture_id,
        )

        logger.info(
            "embedding_search_completed",
            collection_id=request.collection_id,
            results_count=len(top_results),
            documents_scanned=len(documents),
            venture_id=venture_id,
        )

        return SearchResult(
            results=top_results,
            query_embedding_cost_usd=query_cost,
        )

    async def chunk_text(
        self, text: str, strategy: str, chunk_size: int, overlap: int
    ) -> ChunkResult:
        """Public utility to chunk text without embedding."""
        chunks = _chunk_text(text, strategy=strategy, chunk_size=chunk_size, overlap=overlap)
        return ChunkResult(
            chunks=chunks,
            strategy=strategy,
            total_chunks=len(chunks),
        )

    async def delete_collection(self, venture_id: str, collection_id: str) -> None:
        """Soft-delete a collection and its documents."""
        from datetime import UTC, datetime

        async with self._tracer.span(
            "embedding_engine",
            "delete_collection",
            input_data={"collection_id": collection_id},
        ):
            async with get_session(venture_id) as session:
                # Verify collection exists
                result = await session.execute(
                    select(EmbeddingCollection).where(
                        EmbeddingCollection.id == collection_id,
                        EmbeddingCollection.venture_id == venture_id,
                        EmbeddingCollection.deleted_at.is_(None),
                    )
                )
                collection = result.scalar_one_or_none()
                if collection is None:
                    raise ValueError(
                        f"Collection {collection_id} not found for venture {venture_id}"
                    )

                now = datetime.now(UTC)

                # Soft-delete all documents in the collection
                await session.execute(
                    update(EmbeddingDocument)
                    .where(
                        EmbeddingDocument.collection_id == collection_id,
                        EmbeddingDocument.deleted_at.is_(None),
                    )
                    .values(deleted_at=now)
                )

                # Soft-delete the collection itself
                await session.execute(
                    update(EmbeddingCollection)
                    .where(EmbeddingCollection.id == collection_id)
                    .values(deleted_at=now, status="archived")
                )

        logger.info(
            "embedding_collection_deleted",
            collection_id=collection_id,
            venture_id=venture_id,
        )

    async def _generate_embeddings(
        self, texts: list[str], model_name: str
    ) -> tuple[list[list[float]], float]:
        """Call OpenAI embeddings API and return vectors + cost.

        Args:
            texts: List of texts to embed (must be <= MAX_BATCH_SIZE).
            model_name: The embedding model to use.

        Returns:
            Tuple of (list of embedding vectors, estimated cost in USD).
        """
        async with self._tracer.span(
            "embedding_engine",
            "generate_embeddings_api",
            input_data={"text_count": len(texts), "model": model_name},
        ) as span:
            cost = _estimate_cost(texts, model_name)

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    OPENAI_EMBEDDINGS_URL,
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": model_name, "input": texts},
                )
                response.raise_for_status()

            data = response.json()
            embeddings = [item["embedding"] for item in data["data"]]

            # Use actual token usage if available
            usage = data.get("usage", {})
            if usage.get("total_tokens"):
                cost_per_1k = MODEL_COSTS.get(model_name, 0.00002)
                cost = (usage["total_tokens"] / 1000) * cost_per_1k

            span.set_cost(
                cost_usd=cost,
                tokens_input=usage.get("total_tokens", sum(_estimate_tokens(t) for t in texts)),
                model=model_name,
            )
            span.output_data = {
                "embeddings_count": len(embeddings),
                "dimensions": len(embeddings[0]) if embeddings else 0,
            }

            return embeddings, cost


def _metadata_matches(doc_metadata: dict, filter_metadata: dict) -> bool:
    """Check if document metadata matches all filter criteria.

    Simple equality matching on all keys in filter_metadata.
    """
    if not doc_metadata:
        return False
    for key, value in filter_metadata.items():
        if doc_metadata.get(key) != value:
            return False
    return True
