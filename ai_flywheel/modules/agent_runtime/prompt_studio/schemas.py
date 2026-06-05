"""Prompt Studio Pydantic schemas for request/response validation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PromptTemplateCreate(BaseModel):
    """Schema for creating a new prompt template."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    template_text: str = Field(..., min_length=1)
    input_variables: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    category: str | None = None


class PromptTemplateUpdate(BaseModel):
    """Schema for updating an existing prompt template."""

    name: str | None = None
    description: str | None = None
    template_text: str | None = None
    tags: list[str] | None = None
    category: str | None = None
    is_active: bool | None = None
    change_description: str | None = None


class PromptTemplateResponse(BaseModel):
    """Schema for prompt template responses."""

    id: str
    venture_id: str
    name: str
    description: str | None
    template_text: str
    input_variables: list[str]
    tags: list[str]
    category: str | None
    is_active: bool
    current_version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromptVersionResponse(BaseModel):
    """Schema for prompt version history entries."""

    id: str
    template_id: str
    version_number: int
    template_text: str
    input_variables: list[str]
    change_description: str | None
    created_by: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptRenderRequest(BaseModel):
    """Schema for rendering a prompt template with variables."""

    template_id: str | None = None
    template_name: str | None = None
    variables: dict[str, str] = Field(default_factory=dict)


class PromptRenderResponse(BaseModel):
    """Schema for rendered prompt output."""

    rendered_text: str
    template_id: str
    version_used: int
