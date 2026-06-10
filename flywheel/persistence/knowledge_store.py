"""``knowledge-store`` — the easy-to-consume output of ingestion.

Protocol + in-memory fake. Holds both halves of the knowledge-builder's output:

  - **Knowledge graph:** ``Entity`` nodes (idempotent on ``(type, key)``) and
    typed ``Edge`` relationships (idempotent on the full tuple).
  - **Materialized views:** named, denormalized rollups consumers read directly
    (real ``MATERIALIZED VIEW``s on Postgres; refreshable rows in the fake).

Upserts are idempotent so re-running the builder over the same records is safe.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from flywheel.persistence.models import Edge, Entity, MaterializedView


@runtime_checkable
class KnowledgeStore(Protocol):
    def upsert_entities(self, entities: list[Entity]) -> None:
        """Idempotent on ``(venture_id, type, key)``; merges ``props``."""
        ...

    def upsert_edges(self, edges: list[Edge]) -> None:
        """Idempotent on the full relationship tuple."""
        ...

    def refresh_view(self, view: MaterializedView) -> None:
        """Replace a named materialized view's rows wholesale."""
        ...

    def get_view(self, name: str, venture_id: str | None = None) -> MaterializedView | None: ...

    def entities(self, type: str | None = None, venture_id: str | None = None) -> list[Entity]: ...

    def edges(self, type: str | None = None, venture_id: str | None = None) -> list[Edge]: ...


class InMemoryKnowledgeStore:
    """Zero-infra fake. Deterministic ordering for tests."""

    def __init__(self) -> None:
        self._entities: dict[tuple[str, str, str], Entity] = {}
        self._edges: dict[tuple[str, ...], Edge] = {}
        self._views: dict[tuple[str, str], MaterializedView] = {}

    def upsert_entities(self, entities: list[Entity]) -> None:
        for ent in entities:
            key = (ent.venture_id, ent.type, ent.key)
            existing = self._entities.get(key)
            if existing is None:
                self._entities[key] = ent.model_copy(deep=True)
            else:
                merged = {**existing.props, **ent.props}
                self._entities[key] = existing.model_copy(update={"props": merged})

    def upsert_edges(self, edges: list[Edge]) -> None:
        for e in edges:
            key = (
                e.venture_id,
                e.type,
                e.src_type,
                e.src_key,
                e.dst_type,
                e.dst_key,
            )
            self._edges[key] = e.model_copy(deep=True)

    def refresh_view(self, view: MaterializedView) -> None:
        self._views[(view.venture_id, view.name)] = view.model_copy(
            update={"refreshed_at": datetime.now(UTC)}, deep=True
        )

    def get_view(self, name: str, venture_id: str | None = None) -> MaterializedView | None:
        if venture_id is not None:
            v = self._views.get((venture_id, name))
            return v.model_copy(deep=True) if v else None
        # No venture scope: return the first matching by name.
        for (_vid, vname), v in self._views.items():
            if vname == name:
                return v.model_copy(deep=True)
        return None

    def entities(self, type: str | None = None, venture_id: str | None = None) -> list[Entity]:
        out = [
            e.model_copy(deep=True)
            for e in self._entities.values()
            if (type is None or e.type == type)
            and (venture_id is None or e.venture_id == venture_id)
        ]
        out.sort(key=lambda e: (e.type, e.key))
        return out

    def edges(self, type: str | None = None, venture_id: str | None = None) -> list[Edge]:
        out = [
            e.model_copy(deep=True)
            for e in self._edges.values()
            if (type is None or e.type == type)
            and (venture_id is None or e.venture_id == venture_id)
        ]
        out.sort(key=lambda e: (e.type, e.src_key, e.dst_key))
        return out
