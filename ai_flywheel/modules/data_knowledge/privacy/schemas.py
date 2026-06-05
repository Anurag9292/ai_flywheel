"""Privacy & PII Engine — Pydantic schemas for API layer."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PIIDetectionItem(BaseModel):
    """A single PII detection within scanned content."""

    pii_type: str
    value: str
    start: int
    end: int
    confidence: float


class ScanRequest(BaseModel):
    """Schema for requesting a PII scan."""

    content: str
    source_module: str = "unknown"
    redact: bool = False


class ScanResult(BaseModel):
    """Result of a PII scan."""

    detections: list[PIIDetectionItem]
    redacted_content: str | None = None
    has_pii: bool
    detection_count: int


class RedactRequest(BaseModel):
    """Schema for requesting content redaction."""

    content: str
    replacement: str = "[REDACTED]"


class RedactResult(BaseModel):
    """Result of content redaction."""

    redacted_content: str
    redactions_made: int


class RetentionPolicyCreate(BaseModel):
    """Schema for creating a retention policy."""

    name: str
    data_category: str  # personal | financial | health | general
    retention_days: int
    action_on_expiry: str = "anonymize"  # delete | anonymize | archive


class RetentionPolicyResponse(BaseModel):
    """Schema for returning a retention policy."""

    id: str
    venture_id: str
    name: str
    data_category: str
    retention_days: int
    action_on_expiry: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
