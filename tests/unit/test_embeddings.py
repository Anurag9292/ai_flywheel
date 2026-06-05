# ruff: noqa: E501
"""Unit tests for Embedding Engine — chunking and cosine similarity."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.data_knowledge.embeddings.chunking import (
    chunk_by_paragraph,
    chunk_by_sentence,
    chunk_fixed,
)
from ai_flywheel.modules.data_knowledge.embeddings.schemas import CollectionCreate
from ai_flywheel.modules.data_knowledge.embeddings.service import (
    EmbeddingEngine,
    cosine_similarity,
)

# ------------------------------------------------------------------
# Pure logic tests — chunking and similarity
# ------------------------------------------------------------------


@patch("ai_flywheel.modules.data_knowledge.embeddings.service.get_tracer")
@patch("ai_flywheel.modules.data_knowledge.embeddings.service.get_event_bus")
@patch("ai_flywheel.modules.data_knowledge.embeddings.service.get_session")
@pytest.mark.asyncio
async def test_create_collection(mock_get_session, mock_get_event_bus, mock_get_tracer):
    """create_collection should persist a collection and emit event."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    # Simulate flush assigning attributes
    def add_side_effect(obj):
        obj.id = "coll-001"
        obj.status = "active"
        obj.document_count = 0
        from datetime import UTC, datetime
        obj.created_at = datetime(2024, 1, 1, tzinfo=UTC)

    mock_session.add.side_effect = add_side_effect

    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    mock_get_session.return_value = session_cm

    mock_event_bus = AsyncMock()
    mock_event_bus.publish = AsyncMock()
    mock_get_event_bus.return_value = mock_event_bus

    mock_tracer = MagicMock()
    mock_span = MagicMock()
    span_cm = AsyncMock()
    span_cm.__aenter__ = AsyncMock(return_value=mock_span)
    span_cm.__aexit__ = AsyncMock(return_value=False)
    mock_tracer.span.return_value = span_cm
    mock_get_tracer.return_value = mock_tracer

    engine = EmbeddingEngine()
    data = CollectionCreate(
        name="test-collection",
        model_name="text-embedding-3-small",
        dimensions=1536,
        chunk_strategy="paragraph",
        chunk_size=512,
        chunk_overlap=50,
    )
    result = await engine.create_collection("ven-001", data)

    assert result.id == "coll-001"
    assert result.name == "test-collection"
    mock_event_bus.publish.assert_awaited_once()
    call_kwargs = mock_event_bus.publish.call_args[1]
    assert call_kwargs["event_type"] == "embedding.collection.created"


def test_chunk_by_paragraph():
    """chunk_by_paragraph should split on double newlines respecting chunk_size."""
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = chunk_by_paragraph(text, chunk_size=100, overlap=0)

    # All three paragraphs fit in one chunk of 100 chars
    assert len(chunks) == 1
    assert "First paragraph." in chunks[0]

    # Force splitting by setting small chunk_size
    chunks_small = chunk_by_paragraph(text, chunk_size=30, overlap=0)
    assert len(chunks_small) >= 2


def test_chunk_by_sentence():
    """chunk_by_sentence should split on sentence boundaries."""
    text = "This is sentence one. This is sentence two. This is sentence three. This is sentence four."
    # Each sentence is ~22 chars; chunk_size=50 should fit about 2 sentences per chunk
    chunks = chunk_by_sentence(text, chunk_size=50, overlap=0)

    assert len(chunks) >= 2
    # First chunk should contain at least one sentence
    assert "sentence one." in chunks[0] or "sentence two." in chunks[0]


def test_chunk_fixed_with_overlap():
    """chunk_fixed should produce overlapping windows."""
    text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    chunks = chunk_fixed(text, chunk_size=10, overlap=3)

    # Step = 10 - 3 = 7
    assert len(chunks) >= 3
    assert chunks[0] == "ABCDEFGHIJ"
    assert chunks[1] == "HIJKLMNOPQ"  # overlaps 3 chars
    # Last chars of chunk 0 overlap with start of chunk 1
    assert chunks[0][-3:] == chunks[1][:3]


def test_cosine_similarity_identical_vectors():
    """cosine_similarity of identical vectors should be 1.0."""
    vec = [1.0, 2.0, 3.0, 4.0]
    assert abs(cosine_similarity(vec, vec) - 1.0) < 1e-6

    # Orthogonal vectors should be 0.0
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [0.0, 1.0, 0.0]
    assert abs(cosine_similarity(vec_a, vec_b) - 0.0) < 1e-6
