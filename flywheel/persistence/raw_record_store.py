"""``raw-record-store`` — append-only, idempotent store of ingested records.

Protocol + in-memory fake. Two properties matter for the ingestion pipeline:

1. **Idempotency** — ``upsert_many`` keys on ``(source_id, external_id)``, so a
   re-scrape of a full snapshot (these public APIs return full lists, but the
   scraper does not assume that) adds *zero* duplicates. Returns the rows that
   were genuinely new.
2. **Incremental watermark** — every stored row gets a monotonic
   ``ingested_seq``; ``read_since(seq)`` lets the knowledge-builder process only
   newly-added rows on each run (and resume from its own watermark).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from flywheel.persistence.models import RawRecord


@runtime_checkable
class RawRecordStore(Protocol):
    def upsert_many(self, records: list[RawRecord]) -> list[RawRecord]:
        """Idempotent insert on ``(source_id, external_id)``. Returns NEW rows
        (with assigned ``ingested_seq``); existing keys are left untouched.
        """
        ...

    def read_since(self, seq: int, *, limit: int | None = None) -> list[RawRecord]:
        """Rows with ``ingested_seq > seq``, in ascending seq order."""
        ...

    def max_seq(self, source_id: str | None = None) -> int:
        """Highest ``ingested_seq`` (optionally for one source); 0 if empty."""
        ...


class InMemoryRawRecordStore:
    """Zero-infra fake with a process-wide monotonic sequence."""

    def __init__(self) -> None:
        # Preserve insertion order; key on (source_id, external_id).
        self._rows: list[RawRecord] = []
        self._keys: set[tuple[str, str]] = set()
        self._seq = 0

    def upsert_many(self, records: list[RawRecord]) -> list[RawRecord]:
        new: list[RawRecord] = []
        for rec in records:
            key = (rec.source_id, rec.external_id)
            if key in self._keys:
                continue  # idempotent: already ingested
            self._seq += 1
            stored = rec.model_copy(
                update={"ingested_seq": self._seq, "ingested_at": datetime.now(UTC)}
            )
            self._rows.append(stored)
            self._keys.add(key)
            new.append(stored.model_copy(deep=True))
        return new

    def read_since(self, seq: int, *, limit: int | None = None) -> list[RawRecord]:
        rows = [r.model_copy(deep=True) for r in self._rows if r.ingested_seq > seq]
        rows.sort(key=lambda r: r.ingested_seq)
        return rows[:limit] if limit is not None else rows

    def max_seq(self, source_id: str | None = None) -> int:
        seqs = [
            r.ingested_seq
            for r in self._rows
            if source_id is None or r.source_id == source_id
        ]
        return max(seqs) if seqs else 0
