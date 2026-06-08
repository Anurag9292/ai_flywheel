"""``inbound-collector`` — derived in PostlineAI Step 5.

A **library tool** (leaf I/O) wrapping a webhook + email-to-bucket endpoint that
receives raw customer input (voice notes, bullet points, emails) and routes it
to the right venture/customer. Pure function calls; no events.

Fake-first per ``new_docs/stack.md``; the real impl (an HTTP webhook receiver /
mailbox poller) swaps in behind the ``InboundCollector`` Protocol when real
inbound must be captured.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class InboundItem(BaseModel):
    customer_id: str
    kind: str = "text"  # "text" | "audio"
    content: str = ""  # text body, or an audio ref when kind == "audio"


@runtime_checkable
class InboundCollector(Protocol):
    def pull(self) -> list[InboundItem]: ...


class FakeInboundCollector:
    """Offline inbound collector. Returns a seeded queue of items, in order.

    Seed it with items in tests/demos; ``pull`` drains them deterministically.
    """

    def __init__(self, items: list[InboundItem] | None = None) -> None:
        self._items = list(items or [])

    def pull(self) -> list[InboundItem]:
        drained, self._items = self._items, []
        return drained
