"""Pydantic schemas for the Universal Ingestor module.

Request/response models for the ingestor service layer.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DataSourceCreate(BaseModel):
    """Request to create a new data source."""

    name: str
    source_type: str  # csv, json, pdf, html, api, text
    config: dict = Field(default_factory=dict)


class DataSourceResponse(BaseModel):
    """Response containing data source details."""

    id: str
    venture_id: str
    name: str
    source_type: str
    config: dict
    status: str
    last_ingestion_at: datetime | None
    record_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class IngestRequest(BaseModel):
    """Request to ingest data — from a source, raw string, or file."""

    source_id: str | None = None
    raw_data: str | None = None
    file_path: str | None = None
    format: str | None = None  # csv, json, html, text — auto-detected if None
    metadata: dict = Field(default_factory=dict)


class IngestResult(BaseModel):
    """Result of an ingestion run."""

    ingestion_id: str
    source_id: str | None
    status: str  # completed, failed
    records_processed: int
    records_failed: int
    schema_detected: dict | None = None
    duration_ms: float
    errors: list[str] = Field(default_factory=list)


class ParsedRecord(BaseModel):
    """A single parsed record from ingestion."""

    data: dict
    source_field_types: dict  # field_name -> inferred type string
    row_index: int | None = None
