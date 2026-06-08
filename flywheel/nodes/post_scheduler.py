"""``post-scheduler`` — derived in PostlineAI Step 5.

> *The venture needs to: schedule and publish posts at the right time.*

An **event-driven node** that reacts to ``post.approved``, emits
``post.scheduled``, and then publishes via the ``linkedin-posting-client``,
emitting ``post.published``.

- **Reacts to:** ``post.approved``. *(The walkthrough also lists a ``tick.minute``
  timer so scheduled posts publish at their slot — deferred: no timer substrate
  yet. For now an approved post is treated as "publish now". See TODO.)*
- **Calls:** ``linkedin-posting-client``.
- **Emits:** ``post.scheduled``, ``post.published``.
- **Kind:** dumb.
"""

from __future__ import annotations

from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.linkedin_posting_client import (
    FakeLinkedInPostingClient,
    LinkedInPostingClient,
)

# TODO(timers): react to ``tick.minute`` and publish at the scheduled slot once a
# timer substrate exists. For now, approval means publish immediately.


class PostScheduler:
    name = "post-scheduler"
    version = "0.1.0"
    kind = "dumb"
    reacts_to = ["post.approved"]
    emits = ["post.scheduled", "post.published"]
    calls = ["linkedin-posting-client"]

    def __init__(self, *, posting: LinkedInPostingClient | None = None) -> None:
        self._posting = posting or FakeLinkedInPostingClient()

    def handle(self, event: Event, ctx: NodeContext) -> None:
        customer_id = event.payload.get("customer_id", "")
        draft = event.payload.get("draft", "")

        ctx.emit(
            type="post.scheduled",
            payload={"customer_id": customer_id, "draft": draft},
        )

        # Publish-now (timer deferred): push to LinkedIn and announce it.
        published = self._posting.publish(customer_id, draft)
        ctx.emit(type="post.published", payload=published.model_dump())
