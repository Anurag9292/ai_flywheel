"""``post-analytics-collector`` — derived in PostlineAI Step 6.

> *The venture needs to: pull engagement metrics for each customer's published
> posts.*

An **event-driven node** that reacts to ``post.published``, reads engagement via
the existing ``linkedin-posting-client`` read endpoints, and emits
``post.metrics.updated``. A sibling of ``ad-analytics-collector`` — different
domain, different events (the walkthrough's deliberate choice not to overload
the ad collector).

- **Reacts to:** ``post.published``. *(The walkthrough also lists a ``tick.daily``
  timer to refresh metrics on a cadence — deferred: no timer substrate yet.
  See TODO.)*
- **Calls:** ``linkedin-posting-client`` (read endpoints).
- **Emits:** ``post.metrics.updated``.
- **Kind:** dumb.
"""

from __future__ import annotations

from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.linkedin_posting_client import (
    FakeLinkedInPostingClient,
    LinkedInPostingClient,
)

# TODO(timers): also react to ``tick.daily`` to refresh metrics on a cadence
# once a timer substrate exists. For now, collect once when a post is published.


class PostAnalyticsCollector:
    name = "post-analytics-collector"
    version = "0.1.0"
    kind = "dumb"
    reacts_to = ["post.published"]
    emits = ["post.metrics.updated"]
    calls = ["linkedin-posting-client"]

    def __init__(self, *, posting: LinkedInPostingClient | None = None) -> None:
        self._posting = posting or FakeLinkedInPostingClient()

    def handle(self, event: Event, ctx: NodeContext) -> None:
        post_id = event.payload.get("post_id")
        if not post_id:
            return
        metrics = self._posting.get_post_metrics(post_id)
        payload = metrics.model_dump()
        payload["customer_id"] = event.payload.get("customer_id", "")
        ctx.emit(type="post.metrics.updated", payload=payload)
