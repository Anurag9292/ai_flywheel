"""``billing-client`` — derived in PostlineAI Step 5.

A **library tool** (leaf I/O) wrapping Stripe for subscriptions and payments.
Pure function calls; no events.

Fake-first per ``new_docs/stack.md``; the real Stripe impl swaps in behind the
``BillingClient`` Protocol when real money moves.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class Subscription(BaseModel):
    subscription_id: str
    customer_id: str
    plan: str
    amount_usd: float
    status: str = "active"  # "active" | "cancelled"


class Payment(BaseModel):
    payment_id: str
    customer_id: str
    amount_usd: float
    status: str = "captured"  # "captured" | "failed"


@runtime_checkable
class BillingClient(Protocol):
    def create_subscription(
        self, customer_id: str, plan: str, amount_usd: float
    ) -> Subscription: ...

    def capture_payment(self, customer_id: str, amount_usd: float) -> Payment: ...

    def cancel_subscription(self, subscription_id: str) -> Subscription: ...


class FakeBillingClient:
    """Offline billing client. Records subscriptions/payments in memory.

    Ids derive from creation order so output is reproducible without Stripe.
    """

    def __init__(self) -> None:
        self.subscriptions: list[Subscription] = []
        self.payments: list[Payment] = []

    def create_subscription(
        self, customer_id: str, plan: str, amount_usd: float
    ) -> Subscription:
        sub = Subscription(
            subscription_id=f"sub-{len(self.subscriptions) + 1}",
            customer_id=customer_id,
            plan=plan,
            amount_usd=amount_usd,
        )
        self.subscriptions.append(sub)
        return sub

    def capture_payment(self, customer_id: str, amount_usd: float) -> Payment:
        pay = Payment(
            payment_id=f"pay-{len(self.payments) + 1}",
            customer_id=customer_id,
            amount_usd=amount_usd,
        )
        self.payments.append(pay)
        return pay

    def cancel_subscription(self, subscription_id: str) -> Subscription:
        for sub in self.subscriptions:
            if sub.subscription_id == subscription_id:
                sub.status = "cancelled"
                return sub
        # Unknown id: return a synthetic cancelled record (dumb, no raise).
        return Subscription(
            subscription_id=subscription_id,
            customer_id="",
            plan="",
            amount_usd=0.0,
            status="cancelled",
        )
