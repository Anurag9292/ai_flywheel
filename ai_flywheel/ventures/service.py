"""VentureService — CRUD and lifecycle operations for ventures.

All mutations emit events via the event bus for downstream consumers.
Uses global sessions since Ventures are a platform-level (non-RLS) table.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import select

from ai_flywheel.core.contracts.schemas import VentureInfo
from ai_flywheel.core.database import get_global_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.models import Venture

logger = structlog.get_logger()


class VentureService:
    """Manages the full lifecycle of ventures."""

    SOURCE_MODULE = "ventures"

    async def create_venture(
        self,
        name: str,
        domain: str,
        config: dict | None = None,
    ) -> VentureInfo:
        """Create a new venture and emit a venture.created event.

        Args:
            name: Unique human-readable name for the venture.
            domain: Business domain description.
            config: Optional JSON configuration dict.

        Returns:
            VentureInfo with the created venture's data.
        """
        async with get_global_session() as session:
            venture = Venture(
                name=name,
                domain=domain,
                config=config or {},
            )
            session.add(venture)
            await session.flush()

            info = self._to_info(venture)

        event_bus = get_event_bus()
        await event_bus.publish(
            event_type="venture.created",
            source_module=self.SOURCE_MODULE,
            payload={"venture_id": info.id, "name": name, "domain": domain},
            venture_id=info.id,
        )

        logger.info(
            "venture_created",
            venture_id=info.id,
            name=name,
            domain=domain,
        )
        return info

    async def get_venture(self, venture_id: str) -> VentureInfo:
        """Retrieve a venture by ID.

        Args:
            venture_id: UUID of the venture.

        Returns:
            VentureInfo for the requested venture.

        Raises:
            ValueError: If the venture does not exist or is soft-deleted.
        """
        async with get_global_session() as session:
            venture = await session.get(Venture, venture_id)
            if venture is None or venture.is_deleted:
                raise ValueError(f"Venture not found: {venture_id}")
            return self._to_info(venture)

    async def list_ventures(
        self, status: str | None = None
    ) -> list[VentureInfo]:
        """List all active (non-deleted) ventures, optionally filtered by status.

        Args:
            status: If provided, only return ventures with this status.

        Returns:
            List of VentureInfo objects.
        """
        async with get_global_session() as session:
            stmt = select(Venture).where(Venture.deleted_at.is_(None))
            if status is not None:
                stmt = stmt.where(Venture.status == status)
            stmt = stmt.order_by(Venture.created_at.desc())

            result = await session.execute(stmt)
            ventures = result.scalars().all()
            return [self._to_info(v) for v in ventures]

    async def update_venture(
        self, venture_id: str, updates: dict
    ) -> VentureInfo:
        """Update a venture's mutable fields.

        Args:
            venture_id: UUID of the venture to update.
            updates: Dict of field names to new values. Only name, domain,
                     status, and config are allowed.

        Returns:
            VentureInfo reflecting the updated state.

        Raises:
            ValueError: If the venture does not exist or is soft-deleted.
        """
        allowed_fields = {"name", "domain", "status", "config"}

        async with get_global_session() as session:
            venture = await session.get(Venture, venture_id)
            if venture is None or venture.is_deleted:
                raise ValueError(f"Venture not found: {venture_id}")

            applied: dict = {}
            for field, value in updates.items():
                if field not in allowed_fields:
                    continue
                if value is not None:
                    setattr(venture, field, value)
                    applied[field] = value

            await session.flush()
            info = self._to_info(venture)

        event_bus = get_event_bus()
        await event_bus.publish(
            event_type="venture.updated",
            source_module=self.SOURCE_MODULE,
            payload={"venture_id": venture_id, "updates": applied},
            venture_id=venture_id,
        )

        logger.info(
            "venture_updated",
            venture_id=venture_id,
            updates=applied,
        )
        return info

    async def archive_venture(self, venture_id: str) -> None:
        """Soft-delete (archive) a venture.

        Args:
            venture_id: UUID of the venture to archive.

        Raises:
            ValueError: If the venture does not exist or is already archived.
        """
        async with get_global_session() as session:
            venture = await session.get(Venture, venture_id)
            if venture is None or venture.is_deleted:
                raise ValueError(f"Venture not found: {venture_id}")

            venture.deleted_at = datetime.now(UTC)
            await session.flush()

        event_bus = get_event_bus()
        await event_bus.publish(
            event_type="venture.archived",
            source_module=self.SOURCE_MODULE,
            payload={"venture_id": venture_id},
            venture_id=venture_id,
        )

        logger.info("venture_archived", venture_id=venture_id)

    @staticmethod
    def _to_info(venture: Venture) -> VentureInfo:
        """Convert a Venture ORM instance to a VentureInfo DTO."""
        return VentureInfo(
            id=venture.id,
            name=venture.name,
            domain=venture.domain,
            status=venture.status,
            config=venture.config,
        )
