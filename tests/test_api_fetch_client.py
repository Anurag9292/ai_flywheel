"""Tests for ``api-fetch-client`` (fake + real httpx with mocked transport)."""

from __future__ import annotations

import httpx
import pytest

from flywheel.libraries.api_fetch_client import (
    AuthConfig,
    FakeApiFetchClient,
    HttpxApiFetchClient,
    _negotiate_content_type,
)


def test_fake_client_returns_canned_body() -> None:
    client = FakeApiFetchClient({"https://x/y": [{"id": "1"}]})
    res = client.fetch("https://x/y")
    assert res.status == 200
    assert res.parsed == [{"id": "1"}]
    assert res.content_type == "json"


def test_fake_client_unknown_url_degrades_to_empty_list() -> None:
    res = FakeApiFetchClient().fetch("https://unknown")
    assert res.parsed == []


@pytest.mark.parametrize(
    "header,expected",
    [
        ("application/json; charset=utf-8", "json"),
        ("application/rss+xml", "rss"),
        ("text/html", "html"),
        ("", "json"),
    ],
)
def test_content_type_negotiation(header: str, expected: str) -> None:
    assert _negotiate_content_type(header) == expected


def test_httpx_client_injects_bearer_and_parses_json(monkeypatch) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        captured["params"] = str(request.url.params)
        return httpx.Response(200, json={"jobs": [{"id": 1}]})

    transport = httpx.MockTransport(handler)

    def fake_get(url, headers=None, params=None, timeout=None):  # noqa: ANN001
        with httpx.Client(transport=transport) as c:
            return c.get(url, headers=headers, params=params)

    # httpx is imported lazily inside fetch(); patch the module-level httpx.get.
    monkeypatch.setattr(httpx, "get", fake_get)

    client = HttpxApiFetchClient()
    res = client.fetch(
        "https://api.example.com/jobs",
        auth=AuthConfig(kind="bearer", token="secret123"),
        params={"updated_after": "2024-01-01"},
    )
    assert res.status == 200
    assert res.parsed == {"jobs": [{"id": 1}]}
    assert captured["auth"] == "Bearer secret123"
    assert "updated_after=2024-01-01" in captured["params"]


def test_httpx_client_query_auth(monkeypatch) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = str(request.url.params)
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(handler)

    def fake_get(url, headers=None, params=None, timeout=None):  # noqa: ANN001
        with httpx.Client(transport=transport) as c:
            return c.get(url, headers=headers, params=params)

    monkeypatch.setattr(httpx, "get", fake_get)

    HttpxApiFetchClient().fetch(
        "https://api.example.com/x", auth=AuthConfig(kind="query", name="api_key", token="K")
    )
    assert "api_key=K" in captured["params"]
