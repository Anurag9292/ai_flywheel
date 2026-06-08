"""``customer-survey`` — derived in PostlineAI Step 6.

> *The venture needs to: ask each customer for an NPS-style rating and capture
> any inbound leads they got.*

An **event-driven node** that reacts to ``survey.requested``, sends the survey
via the existing ``email``/``slack`` libraries, and emits ``survey.responded``
with the captured response.

- **Reacts to:** ``survey.requested``. *(The walkthrough also lists a ``tick.daily``
  timer to send surveys on a cadence — deferred: no timer substrate yet.)*
- **Calls:** ``email-client``, ``slack-client``.
- **Emits:** ``survey.responded``.
- **Kind:** dumb.

Note: a real survey waits for a human to respond — the same park-and-resume
shape as ``human-review-queue`` (a separate ``survey.response.received`` event
would resume it). For now the fake send returns a deterministic response inline
so the chain is demoable; the human-wait variant is the documented next step.
"""

from __future__ import annotations

from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.email_client import EmailClient, FakeEmailClient
from flywheel.libraries.slack_client import FakeSlackClient, SlackClient


class CustomerSurvey:
    name = "customer-survey"
    version = "0.1.0"
    kind = "dumb"
    reacts_to = ["survey.requested"]
    emits = ["survey.responded"]
    calls = ["email-client", "slack-client"]

    def __init__(
        self,
        *,
        email: EmailClient | None = None,
        slack: SlackClient | None = None,
    ) -> None:
        self._email = email or FakeEmailClient()
        self._slack = slack or FakeSlackClient()

    def handle(self, event: Event, ctx: NodeContext) -> None:
        customer_id = event.payload.get("customer_id", "")
        channel = event.payload.get("channel", "email")
        to = event.payload.get("to", f"{customer_id}@example.com")

        if channel == "slack":
            self._slack.post_message(to, "How likely are you to recommend us? (0-10)")
        else:
            self._email.send(to, "Quick favor — how are we doing?", "NPS 0-10 + any leads?")

        # Capture the response. A real survey would wait for the customer; the
        # fake returns a deterministic NPS so the chain is demoable end-to-end.
        nps = int(event.payload.get("nps", 9))
        ctx.emit(
            type="survey.responded",
            payload={
                "customer_id": customer_id,
                "nps": nps,
                "leads": event.payload.get("leads", 0),
            },
        )
