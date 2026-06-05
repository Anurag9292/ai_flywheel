"""Universal Ingestor service — main orchestration layer.

Handles data source management, format detection, parsing, and record storage.
Emits events for inter-module communication and traces all operations.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.traces import get_tracer

from .models import DataSource, IngestionRecord
from .parsers import get_parser
from .schemas import (
    DataSourceCreate,
    DataSourceResponse,
    IngestRequest,
    IngestResult,
    ParsedRecord,
)

logger = structlog.get_logger()

MODULE_NAME = "data_knowledge.ingestor"


class UniversalIngestor:
    """Service class for ingesting data from multiple formats and sources."""

    def __init__(self) -> None:
        self._event_bus = get_event_bus()
        self._tracer = get_tracer()

    async def create_source(
        self, venture_id: str, data: DataSourceCreate
    ) -> DataSourceResponse:
        """Create a new data source configuration."""
        async with self._tracer.span(MODULE_NAME, "create_source") as span:
            span.input_data = {"venture_id": venture_id, "name": data.name}

            async with get_session(venture_id) as session:
                source = DataSource(
                    venture_id=venture_id,
                    name=data.name,
                    source_type=data.source_type,
                    config=data.config,
                    status="active",
                    record_count=0,
                )
                session.add(source)
                await session.flush()

                response = DataSourceResponse(
                    id=source.id,
                    venture_id=source.venture_id,
                    name=source.name,
                    source_type=source.source_type,
                    config=source.config,
                    status=source.status,
                    last_ingestion_at=source.last_ingestion_at,
                    record_count=source.record_count,
                    created_at=source.created_at,
                )

            await self._event_bus.publish(
                event_type="ingestor.source.created",
                source_module=MODULE_NAME,
                payload={
                    "source_id": response.id,
                    "name": response.name,
                    "source_type": response.source_type,
                },
                venture_id=venture_id,
            )

            logger.info(
                "source_created",
                source_id=response.id,
                name=response.name,
                venture_id=venture_id,
            )
            return response

    async def get_source(
        self, venture_id: str, source_id: str
    ) -> DataSourceResponse | None:
        """Get a data source by ID."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(DataSource).where(
                    DataSource.id == source_id,
                    DataSource.venture_id == venture_id,
                    DataSource.deleted_at.is_(None),
                )
            )
            source = result.scalar_one_or_none()

            if source is None:
                return None

            return DataSourceResponse(
                id=source.id,
                venture_id=source.venture_id,
                name=source.name,
                source_type=source.source_type,
                config=source.config,
                status=source.status,
                last_ingestion_at=source.last_ingestion_at,
                record_count=source.record_count,
                created_at=source.created_at,
            )

    async def list_sources(self, venture_id: str) -> list[DataSourceResponse]:
        """List all data sources for a venture."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(DataSource).where(
                    DataSource.venture_id == venture_id,
                    DataSource.deleted_at.is_(None),
                )
            )
            sources = result.scalars().all()

            return [
                DataSourceResponse(
                    id=s.id,
                    venture_id=s.venture_id,
                    name=s.name,
                    source_type=s.source_type,
                    config=s.config,
                    status=s.status,
                    last_ingestion_at=s.last_ingestion_at,
                    record_count=s.record_count,
                    created_at=s.created_at,
                )
                for s in sources
            ]

    async def ingest(self, venture_id: str, request: IngestRequest) -> IngestResult:
        """Main ingestion method: detects format, parses, validates, stores records.

        Can ingest from:
        - An existing source (by source_id)
        - Raw data string (raw_data)
        - A file path (file_path)
        """
        async with self._tracer.span(MODULE_NAME, "ingest") as span:
            span.input_data = {
                "venture_id": venture_id,
                "source_id": request.source_id,
                "format": request.format,
                "has_raw_data": request.raw_data is not None,
                "file_path": request.file_path,
            }

            start_time = time.perf_counter()
            errors: list[str] = []

            # Create ingestion record
            async with get_session(venture_id) as session:
                ingestion = IngestionRecord(
                    venture_id=venture_id,
                    source_id=request.source_id,
                    status="pending",
                    extra_metadata=request.metadata,
                )
                session.add(ingestion)
                await session.flush()
                ingestion_id = ingestion.id

            # Emit started event
            await self._event_bus.publish(
                event_type="ingestor.ingestion.started",
                source_module=MODULE_NAME,
                payload={
                    "ingestion_id": ingestion_id,
                    "source_id": request.source_id,
                },
                venture_id=venture_id,
            )

            try:
                # Resolve content
                content = await self._resolve_content(venture_id, request)
                if content is None:
                    raise ValueError(
                        "No content to ingest. Provide source_id, raw_data, or file_path."
                    )

                # Detect format
                fmt = request.format or self.detect_format(content)

                # Update ingestion status
                async with get_session(venture_id) as session:
                    result = await session.execute(
                        select(IngestionRecord).where(
                            IngestionRecord.id == ingestion_id
                        )
                    )
                    ingestion_rec = result.scalar_one()
                    ingestion_rec.status = "processing"
                    ingestion_rec.format_detected = fmt
                    ingestion_rec.file_size_bytes = (
                        len(content.encode("utf-8"))
                        if isinstance(content, str)
                        else len(content)
                    )

                # Parse
                parser = get_parser(fmt)
                records = parser.parse(content)

                records_processed = len(records)
                records_failed = 0

                # Detect schema from parsed records
                schema_detected = self._detect_schema(records)

                # Build sample rows for metadata
                sample_rows = [r.data for r in records[:5]]

                # Calculate duration
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Update ingestion record as completed
                async with get_session(venture_id) as session:
                    result = await session.execute(
                        select(IngestionRecord).where(
                            IngestionRecord.id == ingestion_id
                        )
                    )
                    ingestion_rec = result.scalar_one()
                    ingestion_rec.status = "completed"
                    ingestion_rec.records_processed = records_processed
                    ingestion_rec.records_failed = records_failed
                    ingestion_rec.duration_ms = duration_ms
                    ingestion_rec.extra_metadata = {
                        "schema_detected": schema_detected,
                        "sample_rows": sample_rows,
                    }

                    # Update source record count if linked
                    if request.source_id:
                        src_result = await session.execute(
                            select(DataSource).where(
                                DataSource.id == request.source_id
                            )
                        )
                        source = src_result.scalar_one_or_none()
                        if source:
                            source.record_count += records_processed
                            source.last_ingestion_at = datetime.now(UTC)

                # Emit completed event
                await self._event_bus.publish(
                    event_type="ingestor.ingestion.completed",
                    source_module=MODULE_NAME,
                    payload={
                        "ingestion_id": ingestion_id,
                        "source_id": request.source_id,
                        "records_processed": records_processed,
                        "format": fmt,
                        "duration_ms": duration_ms,
                    },
                    venture_id=venture_id,
                )

                logger.info(
                    "ingestion_completed",
                    ingestion_id=ingestion_id,
                    records_processed=records_processed,
                    format=fmt,
                    duration_ms=round(duration_ms, 2),
                    venture_id=venture_id,
                )

                return IngestResult(
                    ingestion_id=ingestion_id,
                    source_id=request.source_id,
                    status="completed",
                    records_processed=records_processed,
                    records_failed=records_failed,
                    schema_detected=schema_detected,
                    duration_ms=duration_ms,
                    errors=errors,
                )

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_msg = f"{type(e).__name__}: {e}"
                errors.append(error_msg)

                # Update ingestion record as failed
                async with get_session(venture_id) as session:
                    result = await session.execute(
                        select(IngestionRecord).where(
                            IngestionRecord.id == ingestion_id
                        )
                    )
                    ingestion_rec = result.scalar_one()
                    ingestion_rec.status = "failed"
                    ingestion_rec.error_message = error_msg
                    ingestion_rec.duration_ms = duration_ms

                # Emit failed event
                await self._event_bus.publish(
                    event_type="ingestor.ingestion.failed",
                    source_module=MODULE_NAME,
                    payload={
                        "ingestion_id": ingestion_id,
                        "source_id": request.source_id,
                        "error": error_msg,
                        "duration_ms": duration_ms,
                    },
                    venture_id=venture_id,
                )

                logger.error(
                    "ingestion_failed",
                    ingestion_id=ingestion_id,
                    error=error_msg,
                    venture_id=venture_id,
                )

                return IngestResult(
                    ingestion_id=ingestion_id,
                    source_id=request.source_id,
                    status="failed",
                    records_processed=0,
                    records_failed=0,
                    schema_detected=None,
                    duration_ms=duration_ms,
                    errors=errors,
                )

    async def ingest_csv(
        self, venture_id: str, content: str, source_name: str | None = None
    ) -> IngestResult:
        """Convenience method to ingest CSV content directly."""
        request = IngestRequest(
            raw_data=content,
            format="csv",
            metadata={"source_name": source_name} if source_name else {},
        )
        return await self.ingest(venture_id, request)

    async def ingest_json(
        self, venture_id: str, content: str, source_name: str | None = None
    ) -> IngestResult:
        """Convenience method to ingest JSON content directly."""
        request = IngestRequest(
            raw_data=content,
            format="json",
            metadata={"source_name": source_name} if source_name else {},
        )
        return await self.ingest(venture_id, request)

    def detect_format(self, content: str | bytes) -> str:
        """Auto-detect format from content heuristics.

        Detection order:
        1. JSON — starts with { or [
        2. HTML — contains <html or <table tags
        3. CSV — consistent comma/tab separation
        4. Text — fallback
        """
        if isinstance(content, bytes):
            text = content.decode("utf-8", errors="replace")
        else:
            text = content

        stripped = text.strip()

        if not stripped:
            return "text"

        # JSON detection — starts with { or [
        if stripped[0] in ("{", "["):
            try:
                import json

                json.loads(stripped)
                return "json"
            except (json.JSONDecodeError, ValueError):
                pass

        # HTML detection — look for common HTML tags
        lower = stripped[:2000].lower()
        if "<html" in lower or "<table" in lower or "<!doctype html" in lower:
            return "html"

        # CSV detection — check for consistent delimiters
        lines = stripped.split("\n", 20)  # Check first 20 lines
        if len(lines) >= 2:
            # Check for consistent comma counts
            comma_counts = [line.count(",") for line in lines[:10] if line.strip()]
            tab_counts = [line.count("\t") for line in lines[:10] if line.strip()]

            if comma_counts and all(c == comma_counts[0] and c > 0 for c in comma_counts):
                return "csv"
            if tab_counts and all(c == tab_counts[0] and c > 0 for c in tab_counts):
                return "csv"

        return "text"

    async def get_ingestion_history(
        self, venture_id: str, source_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get ingestion history, optionally filtered by source."""
        async with get_session(venture_id) as session:
            query = select(IngestionRecord).where(
                IngestionRecord.venture_id == venture_id,
                IngestionRecord.deleted_at.is_(None),
            )

            if source_id:
                query = query.where(IngestionRecord.source_id == source_id)

            query = query.order_by(IngestionRecord.created_at.desc())

            result = await session.execute(query)
            records = result.scalars().all()

            return [
                {
                    "id": r.id,
                    "source_id": r.source_id,
                    "status": r.status,
                    "format_detected": r.format_detected,
                    "records_processed": r.records_processed,
                    "records_failed": r.records_failed,
                    "file_size_bytes": r.file_size_bytes,
                    "duration_ms": r.duration_ms,
                    "error_message": r.error_message,
                    "metadata": r.extra_metadata,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]

    async def _resolve_content(
        self, venture_id: str, request: IngestRequest
    ) -> str | None:
        """Resolve content from the ingest request source."""
        # Direct raw data
        if request.raw_data is not None:
            return request.raw_data

        # File path
        if request.file_path is not None:
            try:
                with open(request.file_path, encoding="utf-8") as f:
                    return f.read()
            except UnicodeDecodeError:
                with open(request.file_path, "rb") as f:
                    return f.read().decode("utf-8", errors="replace")

        # Source-based ingestion (placeholder for API/scheduled sources)
        if request.source_id is not None:
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(DataSource).where(
                        DataSource.id == request.source_id,
                        DataSource.venture_id == venture_id,
                    )
                )
                source = result.scalar_one_or_none()
                if source is None:
                    raise ValueError(f"Source not found: {request.source_id}")

                # For file-based sources, check config for path
                if "file_path" in source.config:
                    try:
                        with open(source.config["file_path"], encoding="utf-8") as f:
                            return f.read()
                    except UnicodeDecodeError:
                        with open(source.config["file_path"], "rb") as f:
                            return f.read().decode("utf-8", errors="replace")

                # For inline data in config
                if "data" in source.config:
                    return source.config["data"]

            return None

        return None

    def _detect_schema(self, records: list[ParsedRecord]) -> dict[str, Any] | None:
        """Detect schema from parsed records."""
        if not records:
            return None

        # Aggregate field types from all records
        field_types: dict[str, dict[str, int]] = {}
        for record in records[:100]:  # Sample first 100 records
            for field, ftype in record.source_field_types.items():
                if field not in field_types:
                    field_types[field] = {}
                field_types[field][ftype] = field_types[field].get(ftype, 0) + 1

        # Pick most common type for each field
        schema: dict[str, str] = {}
        for field, types in field_types.items():
            schema[field] = max(types, key=types.get)  # type: ignore[arg-type]

        return {
            "fields": schema,
            "record_count": len(records),
            "field_count": len(schema),
        }
