"""``human-review-queue`` — derived in PostlineAI Step 5.

The single mechanism for "AI eventually, human for now". It reacts to any event
tagged ``requires_human=true``, **parks** it for a human to review, and — when
the human approves (a separate ``review.approved`` event) — re-emits the
*expected result event type* so the chain resumes.

- **Reacts to:** any event tagged ``requires_human=true`` (e.g. ``post.drafted``),
  plus ``review.approved`` (the resume trigger).
- **Calls:** ``slack-client`` (notify the reviewer).
- **Emits:** the original expected result type (e.g. ``post.approved``), on approval.
- **Kind:** dumb.

## Why park-and-resume (not a blocking wait)

The bus is synchronous: a handler cannot block for hours waiting on a human. So
a human wait is modeled as **two correlated runs**:

  Run 1 (ms): ``post.drafted`` arrives tagged ``requires_human`` → parked here →
              chain ends (this node emits nothing).
  Run 2 (later): ``review.approved`` (carrying the parked ``event_id``) → this
              node re-emits ``post.approved`` with the *same* correlation id →
              the chain resumes (post-scheduler, etc.).

Because Run 2 inherits Run 1's ``correlation_id``, the trace timeline stitches
the whole story together across the gap.

Parked items live **in memory** for now; durable parking (Postgres) and durable
timers / waits (Temporal) are the documented upgrade path per ``new_docs/stack.md``
— deferred until real customer load demands them.
"""

from __future__ import annotations

from typing import Any

from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.slack_client import FakeSlackClient, SlackClient

# Maps a parked event type -> the result event type to re-emit on approval.
# "emits the original expected result type" (layer1-nodes.md). Generic + extensible.
DEFAULT_RESULT_MAP: dict[str, str] = {
    "post.drafted": "post.approved",
}


class HumanReviewQueue:
    name = "human-review-queue"
    version = "0.1.0"
    kind = "dumb"
    # Subscribes to the resume trigger (review.approved) and to each human-gated
    # result type it knows how to resume (the keys of DEFAULT_RESULT_MAP). The
    # Runtime can't subscribe by tag, so the parkable types are listed by name;
    # a parked event is only parked if it also carries requires_human=true.
    reacts_to = ["review.approved", *DEFAULT_RESULT_MAP.keys()]
    emits = list(DEFAULT_RESULT_MAP.values())
    calls = ["slack-client"]

    def __init__(
        self,
        *,
        slack: SlackClient | None = None,
        result_map: dict[str, str] | None = None,
        channel: str = "#review",
    ) -> None:
        self._slack = slack or FakeSlackClient()
        self._result_map = dict(result_map or DEFAULT_RESULT_MAP)
        self._channel = channel
        # parked event_id -> the original parked Event (kept to re-emit on approve)
        self._pending: dict[str, Event] = {}
        # Keep subscriptions + topology metadata consistent with the actual map
        # (in case a custom result_map was injected).
        self.reacts_to = ["review.approved", *self._result_map.keys()]
        self.emits = list(self._result_map.values())

    def handle(self, event: Event, ctx: NodeContext) -> None:
        if event.type == "review.approved":
            self._resume(event, ctx)
            return
        # Otherwise this is a candidate for parking — only if it's human-gated
        # and we know what result to emit for it.
        if event.tags.get("requires_human") is True and event.type in self._result_map:
            self._park(event)

    def _park(self, event: Event) -> None:
        self._pending[event.event_id] = event
        preview = str(event.payload.get("draft", event.payload))[:120]
        self._slack.post_message(
            self._channel,
            f"Review needed ({event.type}) for {event.venture_id}: {preview}",
        )
        # Emit nothing: the synchronous chain ends here until a human approves.

    def _resume(self, approval: Event, ctx: NodeContext) -> None:
        target_id = approval.payload.get("event_id", "")
        parked = self._pending.pop(target_id, None)
        if parked is None:
            # Unknown / already-handled approval: dumb no-op.
            return

        result_type = self._result_map[parked.type]
        # Carry the parked payload forward, allowing the approver to override the
        # text (the founder writes the real post here). Same correlation id.
        payload: dict[str, Any] = dict(parked.payload)
        if "draft" in approval.payload:
            payload["draft"] = approval.payload["draft"]
        payload["reviewed"] = True
        ctx.emit(type=result_type, payload=payload)

    def pending(self) -> list[dict[str, Any]]:
        """Read-only snapshot of parked items (for the dev /api/review surface)."""
        return [
            {
                "event_id": e.event_id,
                "type": e.type,
                "venture_id": e.venture_id,
                "correlation_id": e.correlation_id,
                "payload": e.payload,
            }
            for e in self._pending.values()
        ]
