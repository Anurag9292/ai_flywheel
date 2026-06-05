"""Market & Signal Intelligence — Pydantic schemas.

Request/response models for the market intelligence service.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# --- Signal Source ---


class SignalSourceCreate(BaseModel):
    """Create a new signal source."""

    name: str
    source_type: str = Field(
        ..., pattern="^(news|social|jobs|patents|regulatory|funding|custom)$"
    )
    url: str | None = None
    config: dict = Field(default_factory=dict)


class SignalSourceResponse(BaseModel):
    """Signal source read model."""

    id: str
    venture_id: str
    name: str
    source_type: str
    url: str | None
    config: dict
    is_active: bool
    last_scanned_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Market Signal ---


class MarketSignalResponse(BaseModel):
    """A detected market signal."""

    id: str
    signal_type: str
    title: str
    summary: str
    relevance_score: float
    impact_score: float
    tags: list[str]
    detected_at: datetime

    model_config = {"from_attributes": True}


# --- Analyze Signals ---


class AnalyzeSignalsRequest(BaseModel):
    """Request to analyze raw text for market signals."""

    venture_id: str
    domain: str
    signals_text: str
    focus_areas: list[str] = Field(default_factory=list)


class AnalyzeSignalsResult(BaseModel):
    """Result of signal analysis."""

    signals: list[MarketSignalResponse]
    patterns: list[str]
    summary: str


# --- Market Report ---


class MarketReportRequest(BaseModel):
    """Request to generate a market intelligence report."""

    venture_id: str
    domain: str
    report_type: str = "digest"
    period: str = "weekly"
    focus_areas: list[str] = Field(default_factory=list)


class MarketReportResponse(BaseModel):
    """Generated market intelligence report."""

    id: str
    report_type: str
    period: str
    content: str
    signals_analyzed: int
    key_findings: list[str]
    recommendations: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Opportunity Scoring ---


class OpportunityScore(BaseModel):
    """Multi-factor opportunity scoring result."""

    opportunity: str
    market_size_signal: str
    competition_level: str
    timing: str
    overall_score: float = Field(..., ge=0.0, le=1.0)
