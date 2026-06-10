"""Timer substrate — publishes ``tick.*`` events onto the bus.

Several nodes are *timer-driven*: they should re-run on a cadence (the
``source-scraper`` and ``knowledge-builder`` on ``tick.daily``; the walkthrough
also lists ``tick.daily`` on ``ad-analytics-collector`` / ``customer-survey`` and
``tick.minute`` on ``post-scheduler``). Until now there was no timer substrate,
so those triggers were deferred (see the TODOs in those nodes).

This is the minimal substrate that closes that gap. Like the ``trace-recorder``,
a ``TimerSource`` is *substrate*, not a node you wire: it simply publishes a
timer event onto the bus, and any node subscribed to that type reacts through
the normal ``Runtime`` path (and is therefore traced automatically).

Thin first impl per ``new_docs/stack.md``: ``tick()`` is called manually (by the
dev API, a script, or a test) — deterministic and synchronous. A real scheduler
(cron / Temporal cron workflow) drives ``tick()`` in production, behind this same
surface, with **no node change**.
"""

from __future__ import annotations

from typing import Any

from flywheel.core.events import Event, EventBus


class TimerSource:
    """Publishes ``tick.<period>`` events for one or more ventures.

    A timer event carries the same envelope as any other event (so reactions
    inherit ``venture_id`` / ``correlation_id`` and are traced). ``period`` is a
    free string; ``"daily"`` and ``"minute"`` are the conventions in use.
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    def tick(
        self,
        period: str,
        *,
        venture_id: str,
        payload: dict[str, Any] | None = None,
    ) -> Event:
        """Publish one ``tick.<period>`` event for ``venture_id``.

        Returns the published event so callers/tests can correlate.
        """
        event = Event(
            type=f"tick.{period}",
            venture_id=venture_id,
            payload=payload or {},
        )
        self._bus.publish(event)
        return event

    def tick_daily(self, *, venture_id: str, payload: dict[str, Any] | None = None) -> Event:
        return self.tick("daily", venture_id=venture_id, payload=payload)

    def tick_minute(self, *, venture_id: str, payload: dict[str, Any] | None = None) -> Event:
        return self.tick("minute", venture_id=venture_id, payload=payload)
