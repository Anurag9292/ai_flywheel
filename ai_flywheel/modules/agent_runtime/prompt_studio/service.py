"""Prompt Studio service — template management, versioning, and rendering.

Provides CRUD for prompt templates with automatic version tracking,
rollback support, and Jinja2 rendering with variable injection.
"""

from __future__ import annotations

import jinja2
import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus

from .models import PromptTemplate, PromptVersion
from .schemas import (
    PromptRenderRequest,
    PromptRenderResponse,
    PromptTemplateCreate,
    PromptTemplateResponse,
    PromptTemplateUpdate,
    PromptVersionResponse,
)

logger = structlog.get_logger()

SOURCE_MODULE = "prompt_studio"


class PromptStudioError(Exception):
    """Base error for Prompt Studio operations."""

    pass


class TemplateNotFoundError(PromptStudioError):
    """Raised when a requested template does not exist."""

    pass


class VersionNotFoundError(PromptStudioError):
    """Raised when a requested version does not exist."""

    pass


class RenderError(PromptStudioError):
    """Raised when template rendering fails."""

    pass


class PromptStudio:
    """Service for managing prompt templates with versioning and rendering."""

    def __init__(self) -> None:
        self._event_bus = get_event_bus()
        self._jinja_env = jinja2.Environment(
            undefined=jinja2.StrictUndefined,
            autoescape=False,
        )

    async def create_template(
        self,
        venture_id: str,
        data: PromptTemplateCreate,
    ) -> PromptTemplateResponse:
        """Create a new prompt template with initial version."""
        async with get_session(venture_id) as session:
            template = PromptTemplate(
                venture_id=venture_id,
                name=data.name,
                description=data.description,
                template_text=data.template_text,
                input_variables=data.input_variables,
                tags=data.tags,
                category=data.category,
                is_active=True,
                current_version=1,
            )
            session.add(template)
            await session.flush()

            # Create initial version record
            version = PromptVersion(
                venture_id=venture_id,
                template_id=template.id,
                version_number=1,
                template_text=data.template_text,
                input_variables=data.input_variables,
                change_description="Initial version",
                created_by=None,
            )
            session.add(version)
            await session.flush()

            response = PromptTemplateResponse.model_validate(template)

        await self._event_bus.publish(
            event_type="prompt.created",
            source_module=SOURCE_MODULE,
            payload={
                "template_id": response.id,
                "name": response.name,
                "category": response.category,
            },
            venture_id=venture_id,
        )

        logger.info(
            "prompt_template_created",
            template_id=response.id,
            name=response.name,
            venture_id=venture_id,
        )

        return response

    async def get_template(
        self,
        venture_id: str,
        template_id: str,
    ) -> PromptTemplateResponse:
        """Get a prompt template by ID."""
        async with get_session(venture_id) as session:
            stmt = select(PromptTemplate).where(
                PromptTemplate.id == template_id,
                PromptTemplate.venture_id == venture_id,
                PromptTemplate.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            template = result.scalar_one_or_none()

            if template is None:
                raise TemplateNotFoundError(
                    f"Template '{template_id}' not found for venture '{venture_id}'"
                )

            return PromptTemplateResponse.model_validate(template)

    async def get_template_by_name(
        self,
        venture_id: str,
        name: str,
    ) -> PromptTemplateResponse:
        """Get a prompt template by name within a venture."""
        async with get_session(venture_id) as session:
            stmt = select(PromptTemplate).where(
                PromptTemplate.name == name,
                PromptTemplate.venture_id == venture_id,
                PromptTemplate.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            template = result.scalar_one_or_none()

            if template is None:
                raise TemplateNotFoundError(
                    f"Template with name '{name}' not found for venture '{venture_id}'"
                )

            return PromptTemplateResponse.model_validate(template)

    async def list_templates(
        self,
        venture_id: str,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> list[PromptTemplateResponse]:
        """List prompt templates with optional category and tag filters."""
        async with get_session(venture_id) as session:
            stmt = select(PromptTemplate).where(
                PromptTemplate.venture_id == venture_id,
                PromptTemplate.deleted_at.is_(None),
            )

            if category is not None:
                stmt = stmt.where(PromptTemplate.category == category)

            if tags:
                # Filter templates that contain ALL specified tags
                for tag in tags:
                    stmt = stmt.where(PromptTemplate.tags.contains([tag]))

            stmt = stmt.order_by(PromptTemplate.created_at.desc())
            result = await session.execute(stmt)
            templates = result.scalars().all()

            return [
                PromptTemplateResponse.model_validate(t) for t in templates
            ]

    async def update_template(
        self,
        venture_id: str,
        template_id: str,
        data: PromptTemplateUpdate,
    ) -> PromptTemplateResponse:
        """Update a prompt template. Creates a new version if template_text changes."""
        async with get_session(venture_id) as session:
            stmt = (
                select(PromptTemplate)
                .where(
                    PromptTemplate.id == template_id,
                    PromptTemplate.venture_id == venture_id,
                    PromptTemplate.deleted_at.is_(None),
                )
                .options(selectinload(PromptTemplate.versions))
            )
            result = await session.execute(stmt)
            template = result.scalar_one_or_none()

            if template is None:
                raise TemplateNotFoundError(
                    f"Template '{template_id}' not found for venture '{venture_id}'"
                )

            # Track whether template_text changed (requires new version)
            text_changed = (
                data.template_text is not None
                and data.template_text != template.template_text
            )

            # Apply updates
            if data.name is not None:
                template.name = data.name
            if data.description is not None:
                template.description = data.description
            if data.tags is not None:
                template.tags = data.tags
            if data.category is not None:
                template.category = data.category
            if data.is_active is not None:
                template.is_active = data.is_active

            if text_changed:
                # Parse input variables from new template text
                input_variables = self._extract_variables(data.template_text)
                template.template_text = data.template_text
                template.input_variables = input_variables
                template.current_version += 1

                # Save new version
                version = PromptVersion(
                    venture_id=venture_id,
                    template_id=template.id,
                    version_number=template.current_version,
                    template_text=data.template_text,
                    input_variables=input_variables,
                    change_description=data.change_description,
                    created_by=None,
                )
                session.add(version)

            await session.flush()
            response = PromptTemplateResponse.model_validate(template)

        await self._event_bus.publish(
            event_type="prompt.updated",
            source_module=SOURCE_MODULE,
            payload={
                "template_id": response.id,
                "name": response.name,
                "version": response.current_version,
                "text_changed": text_changed,
            },
            venture_id=venture_id,
        )

        logger.info(
            "prompt_template_updated",
            template_id=response.id,
            version=response.current_version,
            text_changed=text_changed,
            venture_id=venture_id,
        )

        return response

    async def rollback_template(
        self,
        venture_id: str,
        template_id: str,
        version_number: int,
    ) -> PromptTemplateResponse:
        """Rollback a template to a specific version."""
        async with get_session(venture_id) as session:
            # Get the template
            stmt = select(PromptTemplate).where(
                PromptTemplate.id == template_id,
                PromptTemplate.venture_id == venture_id,
                PromptTemplate.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            template = result.scalar_one_or_none()

            if template is None:
                raise TemplateNotFoundError(
                    f"Template '{template_id}' not found for venture '{venture_id}'"
                )

            # Find the target version
            version_stmt = select(PromptVersion).where(
                PromptVersion.template_id == template_id,
                PromptVersion.version_number == version_number,
            )
            version_result = await session.execute(version_stmt)
            target_version = version_result.scalar_one_or_none()

            if target_version is None:
                raise VersionNotFoundError(
                    f"Version {version_number} not found for template '{template_id}'"
                )

            # Restore template text from target version
            template.template_text = target_version.template_text
            template.input_variables = target_version.input_variables
            template.current_version += 1

            # Create a new version record for the rollback
            rollback_version = PromptVersion(
                venture_id=venture_id,
                template_id=template.id,
                version_number=template.current_version,
                template_text=target_version.template_text,
                input_variables=target_version.input_variables,
                change_description=f"Rollback to version {version_number}",
                created_by=None,
            )
            session.add(rollback_version)
            await session.flush()

            response = PromptTemplateResponse.model_validate(template)

        await self._event_bus.publish(
            event_type="prompt.rolled_back",
            source_module=SOURCE_MODULE,
            payload={
                "template_id": response.id,
                "name": response.name,
                "rolled_back_to": version_number,
                "new_version": response.current_version,
            },
            venture_id=venture_id,
        )

        logger.info(
            "prompt_template_rolled_back",
            template_id=response.id,
            rolled_back_to=version_number,
            new_version=response.current_version,
            venture_id=venture_id,
        )

        return response

    async def render(
        self,
        venture_id: str,
        request: PromptRenderRequest,
    ) -> PromptRenderResponse:
        """Render a prompt template with the given variables."""
        # Resolve template by ID or name
        if request.template_id:
            template = await self.get_template(venture_id, request.template_id)
        elif request.template_name:
            template = await self.get_template_by_name(venture_id, request.template_name)
        else:
            raise RenderError("Either template_id or template_name must be provided")

        # Render with Jinja2
        try:
            jinja_template = self._jinja_env.from_string(template.template_text)
            rendered_text = jinja_template.render(**request.variables)
        except jinja2.UndefinedError as e:
            raise RenderError(
                f"Missing variable in template '{template.name}': {e}"
            ) from e
        except jinja2.TemplateSyntaxError as e:
            raise RenderError(
                f"Syntax error in template '{template.name}': {e}"
            ) from e
        except Exception as e:
            raise RenderError(
                f"Failed to render template '{template.name}': {e}"
            ) from e

        await self._event_bus.publish(
            event_type="prompt.rendered",
            source_module=SOURCE_MODULE,
            payload={
                "template_id": template.id,
                "template_name": template.name,
                "version_used": template.current_version,
                "variables_provided": list(request.variables.keys()),
            },
            venture_id=venture_id,
        )

        logger.debug(
            "prompt_rendered",
            template_id=template.id,
            template_name=template.name,
            version=template.current_version,
            venture_id=venture_id,
        )

        return PromptRenderResponse(
            rendered_text=rendered_text,
            template_id=template.id,
            version_used=template.current_version,
        )

    async def get_version_history(
        self,
        venture_id: str,
        template_id: str,
    ) -> list[PromptVersionResponse]:
        """Get the version history for a template."""
        # Verify template exists
        await self.get_template(venture_id, template_id)

        async with get_session(venture_id) as session:
            stmt = (
                select(PromptVersion)
                .where(
                    PromptVersion.template_id == template_id,
                    PromptVersion.venture_id == venture_id,
                )
                .order_by(PromptVersion.version_number.desc())
            )
            result = await session.execute(stmt)
            versions = result.scalars().all()

            return [
                PromptVersionResponse.model_validate(v) for v in versions
            ]

    def _extract_variables(self, template_text: str) -> list[str]:
        """Extract variable names from a Jinja2 template string."""
        try:
            ast = self._jinja_env.parse(template_text)
            variables = sorted(jinja2.meta.find_undeclared_variables(ast))
            return variables
        except jinja2.TemplateSyntaxError:
            # If we can't parse, return empty list; rendering will fail later
            return []
