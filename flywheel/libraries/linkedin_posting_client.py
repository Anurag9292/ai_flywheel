"""``linkedin-posting-client`` — derived in PostlineAI Step 5.

A **library tool** (leaf I/O) wrapping LinkedIn's *content posting* API — this is
distinct from the ``linkedin-ads-client`` (the Marketing/ads API) from Step 4.
Used to publish approved posts and, later, read their engagement. Pure function
calls; no events.

Fake-first per ``new_docs/stack.md``; the real httpx-backed impl swaps in behind
the ``LinkedInPostingClient`` Protocol when posts must publish for real.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class PublishedPost(BaseModel):
    post_id: str
    customer_id: str
    url: str


class PostMetrics(BaseModel):
    post_id: str
    impressions: int = 0
    reactions: int = 0
    comments: int = 0
    shares: int = 0


@runtime_checkable
class LinkedInPostingClient(Protocol):
    def publish(self, customer_id: str, text: str) -> PublishedPost: ...

    def get_post_metrics(self, post_id: str) -> PostMetrics: ...


class FakeLinkedInPostingClient:
    """Offline posting client. Records published posts in memory, deterministically.

    Post ids/urls derive from publish order so output is reproducible; read
    metrics derive from a stable hash of the post id (added in Step 6 — the
    "read endpoints" the post-analytics-collector needs).
    """

    def __init__(self, metrics: dict[str, PostMetrics] | None = None) -> None:
        self.published: list[PublishedPost] = []
        self._metrics = metrics or {}

    def publish(self, customer_id: str, text: str) -> PublishedPost:
        post_id = f"li-post-{len(self.published) + 1}"
        post = PublishedPost(
            post_id=post_id,
            customer_id=customer_id,
            url=f"https://linkedin.com/posts/{post_id}",
        )
        self.published.append(post)
        return post

    def get_post_metrics(self, post_id: str) -> PostMetrics:
        if post_id in self._metrics:
            return self._metrics[post_id]
        seed = sum(ord(c) for c in post_id)
        impressions = (seed * 29) % 8_000
        return PostMetrics(
            post_id=post_id,
            impressions=impressions,
            reactions=impressions // 40,
            comments=impressions // 400,
            shares=impressions // 800,
        )
