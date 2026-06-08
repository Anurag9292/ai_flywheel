"""``subscription-manager`` — derived in PostlineAI Step 5.

> *The venture needs to: bill the three customers $299.*

An **event-driven node** that reacts to subscription lifecycle requests, calls
the ``billing-client`` (Stripe), and emits the resulting lifecycle events.

- **Reacts to:** ``subscription.requested``, ``subscription.cancellation_requested``.
- **Calls:** ``billing-client``.
- **Emits:** ``subscription.activated``, ``subscription.cancelled``,
  ``payment.captured``.
- **Kind:** dumb.

State (active subscriptions) is in-memory for now; durable billing state
(Postgres) is the documented upgrade path per ``new_docs/stack.md``.
"""

from __future__ import annotations

from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.billing_client import BillingClient, FakeBillingClient


class SubscriptionManager:
    name = "subscription-manager"
    version = "0.1.0"
    kind = "dumb"
    reacts_to = ["subscription.requested", "subscription.cancellation_requested"]
    emits = ["subscription.activated", "subscription.cancelled", "payment.captured"]
    calls = ["billing-client"]

    def __init__(self, *, billing: BillingClient | None = None) -> None:
        self._billing = billing or FakeBillingClient()
        # customer_id -> subscription_id (in-memory; durable state deferred).
        self._active: dict[str, str] = {}

    def handle(self, event: Event, ctx: NodeContext) -> None:
        if event.type == "subscription.requested":
            self._activate(event, ctx)
        elif event.type == "subscription.cancellation_requested":
            self._cancel(event, ctx)

    def _activate(self, event: Event, ctx: NodeContext) -> None:
        customer_id = event.payload.get("customer_id", "")
        plan = event.payload.get("plan", "pro")
        amount = float(event.payload.get("amount_usd", 0.0))

        sub = self._billing.create_subscription(customer_id, plan, amount)
        self._active[customer_id] = sub.subscription_id
        ctx.emit(type="subscription.activated", payload=sub.model_dump())

        payment = self._billing.capture_payment(customer_id, amount)
        ctx.emit(type="payment.captured", payload=payment.model_dump())

    def _cancel(self, event: Event, ctx: NodeContext) -> None:
        customer_id = event.payload.get("customer_id", "")
        sub_id = self._active.pop(customer_id, event.payload.get("subscription_id", ""))
        if not sub_id:
            return
        cancelled = self._billing.cancel_subscription(sub_id)
        ctx.emit(type="subscription.cancelled", payload=cancelled.model_dump())
