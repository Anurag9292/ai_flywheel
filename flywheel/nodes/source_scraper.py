"""``source-scraper`` — derived in the public-data ingestion step.

> *The venture needs to: hit each registered source, extract its records, store
> them reliably, and on the next scheduled run resume from where it left off.*

The **agentic** heart of the ingestion cluster. Handed an *opaque* source, it:

  1. **Fetches** the source (auth-aware) via ``api-fetch-client``.
  2. **Fingerprints** the response shape.
  3. **Infers** the :class:`IngestPlan` with the ``Inferencer`` (LLM) — but only
     **once**: the plan is cached on the source and re-inferred only when the
     fingerprint drifts. Human ``hints`` on the source **override** inferred
     fields.
  4. **Executes** the plan: walks pagination, extracts records, normalizes the
     id + timestamp.
  5. **Upserts** idempotently into ``raw-record-store`` on
     ``(source_id, external_id)`` — re-scraping a full snapshot adds zero dupes.
  6. **Advances the cursor** (max seen timestamp) only on success and persists
     it via ``source-store`` so the next ``tick.daily`` resumes.

- **Reacts to:** ``sources.updated``, ``scrape.requested``, ``tick.daily``.
- **Calls:** ``api-fetch-client``, ``inferencer`` (llm-gateway), ``source-store``,
  ``raw-record-store``.
- **Emits:** ``source.records.ingested`` (per source).
- **Kind:** agentic (it reasons about an unknown source's schema with an LLM).

Low-confidence inference (below ``min_confidence``) emits
``source.inference.low_confidence`` tagged ``requires_human`` so the existing
``human-review-queue`` can park it for a human to supply hints — reuse, no new
review machinery.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from flywheel.core.events import Event
from flywheel.core.inferencer import Inferencer, LLMInferencer
from flywheel.core.node import NodeContext
from flywheel.libraries.api_fetch_client import (
    ApiFetchClient,
    AuthConfig,
    FakeApiFetchClient,
    FetchResult,
)
from flywheel.persistence.models import IngestPlan, RawRecord, Source
from flywheel.persistence.raw_record_store import (
    InMemoryRawRecordStore,
    RawRecordStore,
)
from flywheel.persistence.source_store import InMemorySourceStore, SourceStore

# How an auth_ref resolves to a token. Deferred: a real secret store. For now an
# injected mapping (dev: from env) keyed by auth_ref.
AuthResolver = dict[str, AuthConfig]


class SourceScraper:
    name = "source-scraper"
    version = "0.1.0"
    kind = "agentic"
    reacts_to = ["sources.updated", "scrape.requested", "tick.daily"]
    emits = ["source.records.ingested", "source.inference.low_confidence"]
    calls = ["api-fetch-client", "inferencer", "source-store", "raw-record-store"]

    def __init__(
        self,
        *,
        fetch_client: ApiFetchClient | None = None,
        inferencer: Inferencer | None = None,
        source_store: SourceStore | None = None,
        raw_store: RawRecordStore | None = None,
        auth: AuthResolver | None = None,
        min_confidence: float = 0.3,
        max_pages: int = 50,
    ) -> None:
        self._fetch = fetch_client or FakeApiFetchClient()
        self._inferencer = inferencer or LLMInferencer()
        self._sources = source_store or InMemorySourceStore()
        self._raw = raw_store or InMemoryRawRecordStore()
        self._auth = dict(auth or {})
        self._min_confidence = min_confidence
        self._max_pages = max_pages

    def handle(self, event: Event, ctx: NodeContext) -> None:
        for source in self._sources_to_scrape(event):
            self._scrape_one(source, ctx)

    # ── source selection ─────────────────────────────────────────────────────

    def _sources_to_scrape(self, event: Event) -> list[Source]:
        # A specific source can be targeted; otherwise scrape all enabled.
        sid = event.payload.get("source_id")
        if sid:
            s = self._sources.get(sid)
            return [s] if s and s.enabled else []
        return self._sources.list_enabled(event.venture_id or None)

    # ── the core scrape ──────────────────────────────────────────────────────

    def _scrape_one(self, source: Source, ctx: NodeContext) -> None:
        auth = self._auth.get(source.auth_ref, AuthConfig())
        first = self._fetch.fetch(source.url, auth=auth)
        fingerprint = _fingerprint(first.parsed)

        plan = self._resolve_plan(source, first, fingerprint, ctx)
        if plan is None:
            return  # low-confidence + parked for a human

        cursor_value = source.cursor.get("value")
        records, new_cursor = self._collect_records(source, first, plan, auth, cursor_value)

        stored_new = self._raw.upsert_many(records)
        # Advance the cursor only after a successful store.
        self._sources.save_state(
            source.id,
            ingest_plan=plan,
            schema_fingerprint=fingerprint,
            cursor={"strategy": plan.timestamp_field or "snapshot", "value": new_cursor},
        )
        ctx.emit(
            type="source.records.ingested",
            payload={
                "source_id": source.id,
                "url": source.url,
                "new_count": len(stored_new),
                "max_seq": self._raw.max_seq(source.id),
            },
        )

    def _resolve_plan(
        self, source: Source, sample: FetchResult, fingerprint: str, ctx: NodeContext
    ) -> IngestPlan | None:
        """Reuse the cached plan unless the shape drifted; else (re)infer once."""
        cached = source.ingest_plan
        if cached is not None and source.schema_fingerprint == fingerprint:
            return self._apply_hints(cached, source.hints)

        inferred = self._inferencer.infer(sample)
        if inferred.confidence < self._min_confidence and not source.hints:
            # Too unsure and no human hints to lean on: park for a human.
            ctx.emit(
                type="source.inference.low_confidence",
                payload={
                    "source_id": source.id,
                    "url": source.url,
                    "confidence": inferred.confidence,
                    "inferred_plan": inferred.model_dump(),
                },
                tags={"requires_human": True},
            )
            return None
        return self._apply_hints(inferred, source.hints)

    @staticmethod
    def _apply_hints(plan: IngestPlan, hints: dict[str, Any]) -> IngestPlan:
        """Human hints OVERRIDE inferred fields (any subset of IngestPlan)."""
        if not hints:
            return plan
        fields = type(plan).model_fields
        return plan.model_copy(update={k: v for k, v in hints.items() if k in fields})

    # ── plan execution (pagination + extraction) ───────────────────────────────

    def _collect_records(
        self,
        source: Source,
        first: FetchResult,
        plan: IngestPlan,
        auth: AuthConfig,
        cursor_value: Any,
    ) -> tuple[list[RawRecord], Any]:
        """Walk pages, extract + normalize records, compute the new cursor."""
        records: list[RawRecord] = []
        max_ts: Any = cursor_value
        page = first
        pages = 0
        while True:
            pages += 1
            for raw in _extract_list(page.parsed, plan.record_path):
                if not isinstance(raw, dict):
                    continue
                ext_id = str(_dig(raw, plan.id_field) or "")
                if not ext_id:
                    continue
                ts = _normalize_ts(_dig(raw, plan.timestamp_field), plan.timestamp_format)
                # Incremental: skip records at/under the stored cursor when we
                # have a comparable timestamp cursor.
                if cursor_value and ts is not None and _le(ts, cursor_value, plan):
                    continue
                records.append(
                    RawRecord(
                        source_id=source.id,
                        venture_id=source.venture_id,
                        external_id=ext_id,
                        raw=raw,
                        source_timestamp=ts if isinstance(ts, datetime) else None,
                    )
                )
                max_ts = _max_cursor(max_ts, _raw_ts(_dig(raw, plan.timestamp_field), plan))
            nxt = self._next_page(page, plan, source, auth)
            if nxt is None or pages >= self._max_pages:
                break
            page = nxt
        return records, max_ts

    def _next_page(
        self, page: FetchResult, plan: IngestPlan, source: Source, auth: AuthConfig
    ) -> FetchResult | None:
        pg = plan.pagination
        if pg.kind == "none" or not pg.kind:
            return None
        if pg.kind == "cursor":
            token = _dig(page.parsed, pg.token_path) if pg.token_path else None
            if not token:
                return None
            return self._fetch.fetch(source.url, auth=auth, params={pg.param: token})
        # offset / link_header are deferred for the seed sources (all snapshot).
        return None


# ── helpers (pure) ──────────────────────────────────────────────────────────────


def _fingerprint(parsed: Any) -> str:
    """Stable hash of the *shape* (top-level keys / element type), not content."""
    shape: dict[str, Any]
    if isinstance(parsed, list):
        inner = sorted(parsed[0].keys()) if parsed and isinstance(parsed[0], dict) else []
        shape = {"__list__": inner}
    elif isinstance(parsed, dict):
        shape = {k: type(v).__name__ for k, v in parsed.items()}
    else:
        shape = {"__type__": type(parsed).__name__}
    return hashlib.sha256(json.dumps(shape, sort_keys=True).encode()).hexdigest()[:16]


def _dig(obj: Any, path: str) -> Any:
    """Follow a dotted path into nested dicts; ``""`` returns ``obj`` itself."""
    if not path:
        return obj
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _extract_list(parsed: Any, record_path: str) -> list[Any]:
    located = _dig(parsed, record_path)
    if isinstance(located, list):
        return located
    if isinstance(parsed, list):
        return parsed
    return []


def _normalize_ts(value: Any, fmt: str) -> datetime | None:
    """Parse a source timestamp into a tz-aware UTC datetime, if possible."""
    if value is None or not fmt:
        return None
    try:
        if fmt == "epoch_ms":
            return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
        if fmt == "epoch_s":
            return datetime.fromtimestamp(int(value), tz=UTC)
        if fmt == "iso8601" and isinstance(value, str):
            dt = datetime.fromisoformat(value)
            return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (ValueError, TypeError, OverflowError):
        return None
    return None


def _raw_ts(value: Any, plan: IngestPlan) -> Any:
    """The comparable cursor value to persist (epoch int or ISO string)."""
    if value is None or not plan.timestamp_field:
        return None
    if plan.timestamp_format in ("epoch_ms", "epoch_s"):
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    return value  # ISO strings compare lexicographically when normalized


def _max_cursor(a: Any, b: Any) -> Any:
    if a is None:
        return b
    if b is None:
        return a
    try:
        return a if a >= b else b
    except TypeError:
        return a


def _le(ts: Any, cursor_value: Any, plan: IngestPlan) -> bool:
    """Is this record's timestamp <= the stored cursor (already seen)?"""
    raw = _raw_ts_from_dt(ts, plan)
    if raw is None:
        return False
    try:
        return bool(raw <= cursor_value)
    except TypeError:
        return False


def _raw_ts_from_dt(ts: Any, plan: IngestPlan) -> Any:
    if isinstance(ts, datetime):
        if plan.timestamp_format == "epoch_ms":
            return int(ts.timestamp() * 1000)
        if plan.timestamp_format == "epoch_s":
            return int(ts.timestamp())
        return ts.isoformat()
    return ts
