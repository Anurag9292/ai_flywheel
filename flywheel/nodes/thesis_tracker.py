"""``thesis-tracker`` — derived in PostlineAI Step 1.

> *The venture needs to: capture the hunch in a structured form so its
> assumptions can be tracked and falsified.*

The thesis itself is a venture domain artifact (a YAML file). This node is the
Layer 1 capability that *tracks* it: as evidence arrives, it updates whether
each assumption is supported / contradicted / still untested, and announces the
new state so anyone (the founder-notifier, Layer 3) can react.

- **Reacts to:** ``evidence.collected`` (and, from Step 3 onward, ``pain.extracted``,
  ``signal.verdict``, ``survey.responded`` — added by subscription, no code
  change here).
- **Calls:** *nothing* — pure bookkeeping over venture-scoped state.
- **Emits:** ``thesis.state.updated``.
- **Kind:** dumb (no LLM).

State is in-memory for now. Durable venture state (Postgres) is deferred to
PostlineAI Step 5 per ``new_docs/stack.md``.
"""

from __future__ import annotations

from flywheel.core.events import Event
from flywheel.core.node import NodeContext

# Assumption support states.
SUPPORTED = "supported"
CONTRADICTED = "contradicted"
UNTESTED = "untested"


class ThesisTracker:
    """Maintains per-venture assumption support state.

    An ``evidence.collected`` event payload is expected to carry:
        ``assumption`` (str): the assumption key this evidence bears on.
        ``supports`` (bool): True if it supports, False if it contradicts.
    """

    name = "thesis-tracker"
    version = "0.1.0"
    reacts_to = ["evidence.collected"]

    def __init__(self) -> None:
        # venture_id -> {assumption -> state}
        self._state: dict[str, dict[str, str]] = {}

    def handle(self, event: Event, ctx: NodeContext) -> None:
        assumption = event.payload.get("assumption")
        if not assumption:
            # Nothing actionable; a dumb node simply does nothing.
            return

        supports = bool(event.payload.get("supports", False))
        venture_state = self._state.setdefault(event.venture_id, {})
        venture_state[assumption] = SUPPORTED if supports else CONTRADICTED

        ctx.emit(
            type="thesis.state.updated",
            payload={
                "assumption": assumption,
                "state": venture_state[assumption],
                "thesis": dict(venture_state),
            },
        )

    def state_for(self, venture_id: str) -> dict[str, str]:
        """Read-only helper (tests / inspection). Returns a copy."""
        return dict(self._state.get(venture_id, {}))
