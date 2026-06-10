"""``source-store`` — durable catalog of sources + their resume state.

Protocol + in-memory fake. The ``Sql*`` impl (Neon) lands in
``flywheel/persistence/sql_stores.py`` behind this same interface.

The store owns the *opaque resume state* (``ingest_plan``, ``schema_fingerprint``,
``cursor``) so a scheduled re-run of the scraper picks up where it left off —
the whole point of "start from that point in the next scheduled run".
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from flywheel.persistence.models import IngestPlan, Source


@runtime_checkable
class SourceStore(Protocol):
    def upsert(self, source: Source) -> Source:
        """Insert or update a source by ``id`` (assigning one if empty)."""
        ...

    def get(self, source_id: str) -> Source | None: ...

    def list_enabled(self, venture_id: str | None = None) -> list[Source]:
        """Enabled sources, optionally scoped to a venture."""
        ...

    def save_state(
        self,
        source_id: str,
        *,
        ingest_plan: IngestPlan | None = None,
        schema_fingerprint: str | None = None,
        cursor: dict[str, Any] | None = None,
    ) -> None:
        """Persist resume state after a scrape run (only non-None fields)."""
        ...


class InMemorySourceStore:
    """Zero-infra fake. Deterministic; used by unit tests and the dev demo."""

    def __init__(self) -> None:
        self._by_id: dict[str, Source] = {}

    def upsert(self, source: Source) -> Source:
        sid = source.id or uuid.uuid4().hex
        now = datetime.now(UTC)
        existing = self._by_id.get(sid)
        stored = source.model_copy(
            update={
                "id": sid,
                "updated_at": now,
                "created_at": existing.created_at if existing else source.created_at,
            }
        )
        self._by_id[sid] = stored
        return stored

    def get(self, source_id: str) -> Source | None:
        s = self._by_id.get(source_id)
        return s.model_copy(deep=True) if s else None

    def list_enabled(self, venture_id: str | None = None) -> list[Source]:
        out = [
            s.model_copy(deep=True)
            for s in self._by_id.values()
            if s.enabled and (venture_id is None or s.venture_id == venture_id)
        ]
        # Stable order by creation time then id (deterministic for tests).
        out.sort(key=lambda s: (s.created_at, s.id))
        return out

    def save_state(
        self,
        source_id: str,
        *,
        ingest_plan: IngestPlan | None = None,
        schema_fingerprint: str | None = None,
        cursor: dict[str, Any] | None = None,
    ) -> None:
        src = self._by_id.get(source_id)
        if src is None:
            return
        updates: dict[str, Any] = {"updated_at": datetime.now(UTC)}
        if ingest_plan is not None:
            updates["ingest_plan"] = ingest_plan
        if schema_fingerprint is not None:
            updates["schema_fingerprint"] = schema_fingerprint
        if cursor is not None:
            updates["cursor"] = cursor
        self._by_id[source_id] = src.model_copy(update=updates)
