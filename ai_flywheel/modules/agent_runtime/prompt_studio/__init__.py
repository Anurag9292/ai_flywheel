"""Prompt Studio — template management, versioning, and Jinja2 rendering.

Module #8 of the AI Flywheel platform. Provides:
- CRUD for prompt templates with automatic version tracking
- Rollback to any previous version
- Jinja2-based rendering with strict variable validation
- Event emission for observability (prompt.created, prompt.updated, etc.)
"""

from .models import PromptTemplate, PromptVersion
from .schemas import (
    PromptRenderRequest,
    PromptRenderResponse,
    PromptTemplateCreate,
    PromptTemplateResponse,
    PromptTemplateUpdate,
    PromptVersionResponse,
)
from .service import (
    PromptStudio,
    PromptStudioError,
    RenderError,
    TemplateNotFoundError,
    VersionNotFoundError,
)

__all__ = [
    # Models
    "PromptTemplate",
    "PromptVersion",
    # Schemas
    "PromptRenderRequest",
    "PromptRenderResponse",
    "PromptTemplateCreate",
    "PromptTemplateResponse",
    "PromptTemplateUpdate",
    "PromptVersionResponse",
    # Service
    "PromptStudio",
    # Errors
    "PromptStudioError",
    "RenderError",
    "TemplateNotFoundError",
    "VersionNotFoundError",
]
