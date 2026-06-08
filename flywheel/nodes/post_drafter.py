"""``post-drafter`` — derived in PostlineAI Step 5 (the Wizard-of-Oz node).

> *The venture needs to: turn that input into draft LinkedIn posts.*

An **event-driven node** that reacts to ``input.captured`` and emits
``post.drafted``. **Its first implementation routes to a human** (the founder)
via the ``human-review-queue`` — the event interface stays the same when the
implementation is later swapped for an LLM agent (Step 7). That swap is the
"graduate up the evidence ladder" mechanic: only the binding changes, never the
event contract.

- **Reacts to:** ``input.captured``.
- **Calls:** ``llm-gateway`` *(once the impl is the agent)*; routes through
  ``human-review-queue`` *(while the impl is human)*.
- **Emits:** ``post.drafted``.
- **Kind:** dumb (human binding) → agentic (Step 7).

The pluggable implementation lives behind a ``Drafter`` Protocol, mirroring the
``Agent`` seam used by the agentic nodes. ``HumanDrafter`` produces a
placeholder draft and marks the output ``requires_human=true`` so the
``human-review-queue`` parks it for the founder to write/approve. The chosen
drafter is reflected in the node's ``version`` (e.g. ``0.1.0-human``) so traces
distinguish a human draft from an agent draft.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from flywheel.core.events import Event
from flywheel.core.node import NodeContext


@runtime_checkable
class Drafter(Protocol):
    """Produces a draft from a customer's captured input.

    ``version`` is folded into the node's trace version so a human draft and an
    agent draft are distinguishable in the timeline.
    """

    version: str

    def draft(self, customer_id: str, text: str) -> tuple[str, bool]:
        """Return ``(draft_text, requires_human)``."""
        ...


class HumanDrafter:
    """Wizard-of-Oz drafter: the *founder* writes the post.

    It emits a placeholder draft marked ``requires_human=true``; the
    ``human-review-queue`` then parks it until the founder writes/approves the
    real text. The event interface is identical to a future agent drafter.
    """

    version = "human"

    def draft(self, customer_id: str, text: str) -> tuple[str, bool]:
        placeholder = f"[DRAFT NEEDED] Founder to ghostwrite a post from: {text}"
        return placeholder, True


class PostDrafter:
    name = "post-drafter"
    reacts_to = ["input.captured"]
    emits = ["post.drafted"]
    # While the impl is human, the "call" is the review queue, not the LLM.
    calls = ["human-review-queue"]

    def __init__(self, *, drafter: Drafter | None = None) -> None:
        self._drafter = drafter or HumanDrafter()
        # Binding is reflected in the node version + kind for the trace/topology.
        self.version = f"0.1.0-{self._drafter.version}"
        self.kind = "dumb" if self._drafter.version == "human" else "agentic"

    def handle(self, event: Event, ctx: NodeContext) -> None:
        customer_id = event.payload.get("customer_id", "")
        text = event.payload.get("text", "")

        draft_text, requires_human = self._drafter.draft(customer_id, text)

        # The tag is what the human-review-queue keys off of. When the impl is an
        # agent that needs no review, requires_human is False and the draft flows
        # straight on to scheduling.
        ctx.emit(
            type="post.drafted",
            payload={"customer_id": customer_id, "draft": draft_text},
            tags={"requires_human": requires_human} if requires_human else {},
        )
