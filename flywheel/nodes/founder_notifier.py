"""``founder-notifier`` — derived in PostlineAI Step 4.

> *The venture needs to: surface the verdict to the founder for the go/kill
> decision.*

An **event-driven node** that reacts to decision-relevant events and routes a
notification to the founder via Slack and/or email based on urgency, then emits
``founder.notified``.

- **Reacts to:** ``signal.verdict``, ``thesis.state.updated`` (and, by
  convention, any event tagged ``urgent=true`` — surfaced via the event's
  ``tags``). More result types get added by subscription as the venture grows.
- **Calls:** ``slack-client``, ``email-client``.
- **Emits:** ``founder.notified``.
- **Kind:** dumb (routing, no LLM).

Routing rule (kept dumb): urgent → Slack *and* email; otherwise → email only.
A ``signal.verdict`` of ``kill`` or ``strong`` is treated as urgent (the founder
must decide now); a ``weak`` verdict is not.
"""

from __future__ import annotations

from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.email_client import EmailClient, FakeEmailClient
from flywheel.libraries.slack_client import FakeSlackClient, SlackClient

URGENT_VERDICTS = {"strong", "kill"}


class FounderNotifier:
    name = "founder-notifier"
    version = "0.1.0"
    kind = "dumb"
    reacts_to = ["signal.verdict", "thesis.state.updated"]
    emits = ["founder.notified"]
    calls = ["slack-client", "email-client"]

    def __init__(
        self,
        *,
        slack: SlackClient | None = None,
        email: EmailClient | None = None,
        channel: str = "#ventures",
        founder_email: str = "founder@example.com",
    ) -> None:
        self._slack = slack or FakeSlackClient()
        self._email = email or FakeEmailClient()
        self._channel = channel
        self._founder_email = founder_email

    def handle(self, event: Event, ctx: NodeContext) -> None:
        urgent = self._is_urgent(event)
        summary = self._summarize(event)

        channels: list[str] = []
        if urgent:
            self._slack.post_message(self._channel, summary)
            channels.append("slack")
        self._email.send(self._founder_email, f"[{event.venture_id}] {event.type}", summary)
        channels.append("email")

        ctx.emit(
            type="founder.notified",
            payload={"about": event.type, "urgent": urgent, "via": channels},
        )

    def _is_urgent(self, event: Event) -> bool:
        if event.tags.get("urgent") is True:
            return True
        if event.type == "signal.verdict":
            return event.payload.get("verdict") in URGENT_VERDICTS
        return False

    def _summarize(self, event: Event) -> str:
        if event.type == "signal.verdict":
            return (
                f"Signal verdict: {event.payload.get('verdict')} "
                f"(confidence {event.payload.get('confidence')}) — "
                f"{event.payload.get('explanation', '')}"
            )
        if event.type == "thesis.state.updated":
            return (
                f"Thesis update: {event.payload.get('assumption')} is now "
                f"{event.payload.get('state')}."
            )
        return f"Update: {event.type}"
