"""``api-fetch-client`` — derived in the public-data ingestion step.

A **library tool** (leaf I/O): fetches an arbitrary HTTP source and returns its
**raw body, parsed structure, and response headers**. It is intentionally
*source-agnostic* — it does NOT know Lever/Greenhouse/Ashby or any provider. It
just performs an authenticated HTTP GET, negotiates the content type
(JSON now; RSS/HTML behind the same Protocol later), and hands the parsed body
back. *Interpreting* that body (where the records are, the id/timestamp fields,
how to page) is the agentic ``source-scraper``'s job via the ``Inferencer``.

Per the repo's fake/real seam:
  - ``HttpxApiFetchClient`` — real, uses ``httpx``; supports pluggable auth
    (api-key / bearer / header / query) and content-type negotiation.
  - ``FakeApiFetchClient`` — deterministic, offline; serves canned bodies keyed
    by URL so the scraper + inferencer run end-to-end with no network.

Auth secrets are never stored on the ``Source``; the scraper resolves an
``auth_ref`` to an :class:`AuthConfig` at fetch time (env / secret store).
"""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class AuthConfig(BaseModel):
    """How to authenticate a request. ``kind`` selects the injection strategy.

    - ``"none"``   — no auth (all six seed sources are public).
    - ``"bearer"`` — ``Authorization: Bearer <token>``.
    - ``"header"`` — custom header ``name: token`` (e.g. ``X-API-Key``).
    - ``"query"``  — append ``?<name>=<token>`` to the URL.
    """

    kind: str = "none"
    token: str = ""
    name: str = ""


class FetchResult(BaseModel):
    """What a fetch returns: the parsed body plus enough to drive inference.

    ``parsed`` is the JSON-decoded body (dict or list) when ``content_type`` is
    JSON; for RSS/HTML it is a best-effort structured form (deferred). ``raw``
    keeps the undecoded text so the inferencer can sample it.
    """

    url: str = ""
    status: int = 200
    content_type: str = "json"
    parsed: Any = None
    raw: str = ""
    headers: dict[str, str] = Field(default_factory=dict)


@runtime_checkable
class ApiFetchClient(Protocol):
    def fetch(
        self,
        url: str,
        *,
        auth: AuthConfig | None = None,
        params: dict[str, Any] | None = None,
    ) -> FetchResult:
        ...


def _negotiate_content_type(header_value: str) -> str:
    """Map a Content-Type header to our coarse ``json|rss|html`` bucket."""
    h = (header_value or "").lower()
    if "json" in h:
        return "json"
    if "xml" in h or "rss" in h or "atom" in h:
        return "rss"
    if "html" in h:
        return "html"
    return "json"  # default optimistic for unknown APIs


def _parse_body(text: str, content_type: str) -> Any:
    """Parse a response body into structure. JSON now; RSS/HTML deferred."""
    if content_type == "json":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    # RSS/HTML structured parsing is deferred (stack.md): keep raw text only,
    # the inferencer can still sample ``raw``. Return None to signal "unparsed".
    return None


class HttpxApiFetchClient:
    """Real fetch client. Auth-aware, content-type-negotiating HTTP GET.

    ``httpx`` is imported lazily so the fake path (and the whole test suite)
    never requires the dependency to be installed.
    """

    def __init__(self, *, timeout: float = 20.0, user_agent: str = "ai-flywheel/0.1") -> None:
        self._timeout = timeout
        self._user_agent = user_agent

    def fetch(
        self,
        url: str,
        *,
        auth: AuthConfig | None = None,
        params: dict[str, Any] | None = None,
    ) -> FetchResult:
        import httpx  # lazy: only needed for real fetches

        headers = {"User-Agent": self._user_agent, "Accept": "application/json"}
        query: dict[str, Any] = dict(params or {})
        auth = auth or AuthConfig()
        if auth.kind == "bearer" and auth.token:
            headers["Authorization"] = f"Bearer {auth.token}"
        elif auth.kind == "header" and auth.name and auth.token:
            headers[auth.name] = auth.token
        elif auth.kind == "query" and auth.name and auth.token:
            query[auth.name] = auth.token

        resp = httpx.get(url, headers=headers, params=query, timeout=self._timeout)
        content_type = _negotiate_content_type(resp.headers.get("content-type", ""))
        text = resp.text
        return FetchResult(
            url=str(resp.url),
            status=resp.status_code,
            content_type=content_type,
            parsed=_parse_body(text, content_type),
            raw=text,
            headers=dict(resp.headers),
        )


class FakeApiFetchClient:
    """Offline fetch client returning deterministic canned bodies by URL.

    Seed it with ``{url: parsed_body}`` (any JSON-able structure). Unknown URLs
    return an empty JSON list so the scraper degrades gracefully. ``raw`` is the
    JSON-encoded body so an inferencer that samples text still works.
    """

    def __init__(self, bodies: dict[str, Any] | None = None) -> None:
        self._bodies = dict(bodies or {})

    def add(self, url: str, body: Any) -> None:
        self._bodies[url] = body

    def fetch(
        self,
        url: str,
        *,
        auth: AuthConfig | None = None,
        params: dict[str, Any] | None = None,
    ) -> FetchResult:
        body = self._bodies.get(url, [])
        return FetchResult(
            url=url,
            status=200,
            content_type="json",
            parsed=body,
            raw=json.dumps(body),
            headers={"content-type": "application/json"},
        )
