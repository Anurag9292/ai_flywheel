# ruff: noqa: E501
"""Unit tests for Universal Ingestor — parsers and service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.data_knowledge.ingestor.parsers import (
    CSVParser,
    JSONParser,
)
from ai_flywheel.modules.data_knowledge.ingestor.service import UniversalIngestor

# ------------------------------------------------------------------
# Pure logic tests — format detection and parsing
# ------------------------------------------------------------------


def test_detect_format_csv():
    """detect_format should identify consistent comma-separated content as CSV."""
    content = "name,age,city\nAlice,30,NYC\nBob,25,LA\n"
    ingestor = UniversalIngestor.__new__(UniversalIngestor)
    assert ingestor.detect_format(content) == "csv"


def test_detect_format_json():
    """detect_format should identify content starting with { or [ as JSON."""
    content = '{"name": "Alice", "age": 30}'
    ingestor = UniversalIngestor.__new__(UniversalIngestor)
    assert ingestor.detect_format(content) == "json"

    content_array = '[{"a": 1}, {"a": 2}]'
    assert ingestor.detect_format(content_array) == "json"


def test_detect_format_html():
    """detect_format should identify HTML content."""
    content = "<html><body><p>Hello</p></body></html>"
    ingestor = UniversalIngestor.__new__(UniversalIngestor)
    assert ingestor.detect_format(content) == "html"


def test_parse_csv_records():
    """CSVParser should produce records with correct headers and type inference."""
    csv_content = "name,age,score\nAlice,30,95.5\nBob,25,88.0\n"
    parser = CSVParser()
    records = parser.parse(csv_content)

    assert len(records) == 2
    assert records[0].data["name"] == "Alice"
    assert records[0].data["age"] == 30
    assert records[0].data["score"] == 95.5
    assert records[0].row_index == 0
    assert records[1].row_index == 1


def test_parse_json_array():
    """JSONParser should parse a JSON array into individual records with flattening."""
    json_content = '[{"name": "Alice", "address": {"city": "NYC"}}, {"name": "Bob", "address": {"city": "LA"}}]'
    parser = JSONParser()
    records = parser.parse(json_content)

    assert len(records) == 2
    assert records[0].data["name"] == "Alice"
    assert records[0].data["address.city"] == "NYC"
    assert records[1].data["name"] == "Bob"


@patch("ai_flywheel.modules.data_knowledge.ingestor.service.get_tracer")
@patch("ai_flywheel.modules.data_knowledge.ingestor.service.get_event_bus")
@patch("ai_flywheel.modules.data_knowledge.ingestor.service.get_session")
@pytest.mark.asyncio
async def test_ingest_creates_record_and_emits_event(
    mock_get_session, mock_get_event_bus, mock_get_tracer
):
    """ingest should create an ingestion record and emit events on success."""
    # Mock session
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    # Track objects added to session to assign IDs on flush
    added_objects = []

    def add_side_effect(obj):
        added_objects.append(obj)

    mock_session.add.side_effect = add_side_effect

    flush_count = [0]

    async def flush_side_effect():
        flush_count[0] += 1
        for obj in added_objects:
            if hasattr(obj, "id") and obj.id is None:
                obj.id = f"ing-{flush_count[0]}"
            if hasattr(obj, "created_at") and obj.created_at is None:
                from datetime import UTC, datetime
                obj.created_at = datetime(2024, 1, 1, tzinfo=UTC)

    mock_session.flush = AsyncMock(side_effect=flush_side_effect)

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = MagicMock(
        id="ing-1", status="pending", format_detected=None,
        file_size_bytes=None, records_processed=0, records_failed=0,
        duration_ms=0, error_message=None, metadata={}
    )
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Configure get_session as async context manager
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    mock_get_session.return_value = session_cm

    # Mock event bus
    mock_event_bus = AsyncMock()
    mock_event_bus.publish = AsyncMock()
    mock_get_event_bus.return_value = mock_event_bus

    # Mock tracer
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_span.set_cost = MagicMock()
    span_cm = AsyncMock()
    span_cm.__aenter__ = AsyncMock(return_value=mock_span)
    span_cm.__aexit__ = AsyncMock(return_value=False)
    mock_tracer.span.return_value = span_cm
    mock_get_tracer.return_value = mock_tracer

    from ai_flywheel.modules.data_knowledge.ingestor.schemas import IngestRequest

    ingestor = UniversalIngestor()
    request = IngestRequest(
        raw_data="name,age\nAlice,30\nBob,25\n",
        format="csv",
    )
    result = await ingestor.ingest("ven-001", request)

    assert result.status == "completed"
    assert result.records_processed == 2
    # At least the "started" and "completed" events
    assert mock_event_bus.publish.await_count >= 2
