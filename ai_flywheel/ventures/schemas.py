"""Pydantic schemas for Venture CRUD operations."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class VentureCreate(BaseModel):
    """Schema for creating a new venture."""

    name: str = Field(..., min_length=1, max_length=255)
    domain: str = Field(..., min_length=1)
    config: dict = Field(default_factory=dict)


class VentureUpdate(BaseModel):
    """Schema for updating an existing venture. All fields optional."""

    name: str | None = None
    domain: str | None = None
    status: str | None = None
    config: dict | None = None


class VentureResponse(BaseModel):
    """Full venture representation returned from the API."""

    id: str
    name: str
    domain: str
    status: str
    config: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
