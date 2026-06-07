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

from collections.abc import Callable
from typing import Any

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
    version = "0.2.0"
    kind = "dumb"
    # Step 1 it reacted only to raw evidence. From Step 2+ it *also* reacts to
    # other nodes' result-events (reuse by subscription, per the walkthrough),
    # interpreting each as evidence for a specific assumption via EVIDENCE_MAP.
    reacts_to = [
        "evidence.collected",
        "market.landscape.summarized",
        "pain.extracted",
        "signal.verdict",
        "survey.responded",
    ]
    emits = ["thesis.state.updated"]
    calls: list[str] = []  # pure bookkeeping; no library calls

    # Maps a result-event type -> (assumption, how to read support from payload).
    # Keeps the node "dumb": a lookup + bookkeeping, no LLM. Each reader returns
    # True (supported) / False (contradicted) / None (not actionable).
    EVIDENCE_MAP: dict[str, tuple[str, Callable[[dict[str, Any]], bool | None]]] = {
        # A summarized market landscape that names a gap supports "there is room".
        "market.landscape.summarized": (
            "market_gap_exists",
            lambda p: ("gap" in (p.get("summary", "").lower())) or bool(p.get("competitors")),
        ),
        # Extracted pain supports that the problem is real.
        "pain.extracted": (
            "problem_is_real",
            lambda p: bool(p.get("pains") or p.get("pain_points")),
        ),
        # A signal verdict maps strong->supported, kill->contradicted, weak->n/a.
        "signal.verdict": (
            "demand_validated",
            lambda p: True if p.get("verdict") == "strong"
            else (False if p.get("verdict") == "kill" else None),
        ),
        # A survey response with a positive NPS supports retention.
        "survey.responded": (
            "customers_satisfied",
            lambda p: (p.get("nps") is not None and float(p.get("nps", 0)) >= 0),
        ),
    }

    def __init__(self) -> None:
        # venture_id -> {assumption -> state}
        self._state: dict[str, dict[str, str]] = {}

    def handle(self, event: Event, ctx: NodeContext) -> None:
        assumption, supports = self._read_evidence(event)
        if assumption is None or supports is None:
            # Nothing actionable; a dumb node simply does nothing.
            return

        venture_state = self._state.setdefault(event.venture_id, {})
        venture_state[assumption] = SUPPORTED if supports else CONTRADICTED

        ctx.emit(
            type="thesis.state.updated",
            payload={
                "assumption": assumption,
                "state": venture_state[assumption],
                "evidence_from": event.type,
                "thesis": dict(venture_state),
            },
        )

    def _read_evidence(self, event: Event) -> tuple[str | None, bool | None]:
        """Resolve (assumption, supports) from either a raw evidence event or a
        known result-event via EVIDENCE_MAP.
        """
        if event.type == "evidence.collected":
            assumption = event.payload.get("assumption")
            if not assumption:
                return None, None
            return assumption, bool(event.payload.get("supports", False))

        mapped = self.EVIDENCE_MAP.get(event.type)
        if mapped is None:
            return None, None
        assumption, reader = mapped
        return assumption, reader(event.payload)

    def state_for(self, venture_id: str) -> dict[str, str]:
        """Read-only helper (tests / inspection). Returns a copy."""
        return dict(self._state.get(venture_id, {}))
