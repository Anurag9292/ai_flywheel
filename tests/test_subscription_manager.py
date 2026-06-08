from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.billing_client import FakeBillingClient
from flywheel.nodes.subscription_manager import SubscriptionManager


def _runtime(tmp_path, *nodes):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    for node in nodes:
        runtime.register(node)
    return bus, runtime


def test_activate_emits_activated_and_payment(tmp_path) -> None:
    billing = FakeBillingClient()
    bus, _ = _runtime(tmp_path, SubscriptionManager(billing=billing))
    activated: list[Event] = []
    payments: list[Event] = []
    bus.subscribe("subscription.activated", activated.append)
    bus.subscribe("payment.captured", payments.append)

    bus.publish(Event(
        type="subscription.requested",
        venture_id="postlineai",
        payload={"customer_id": "c1", "plan": "trial", "amount_usd": 299},
    ))

    assert len(activated) == 1
    assert activated[0].payload["status"] == "active"
    assert activated[0].payload["amount_usd"] == 299.0
    assert len(payments) == 1
    assert payments[0].payload["status"] == "captured"


def test_cancel_emits_cancelled(tmp_path) -> None:
    billing = FakeBillingClient()
    mgr = SubscriptionManager(billing=billing)
    bus, _ = _runtime(tmp_path, mgr)
    cancelled: list[Event] = []
    bus.subscribe("subscription.cancelled", cancelled.append)

    bus.publish(Event(
        type="subscription.requested",
        venture_id="postlineai",
        payload={"customer_id": "c1", "plan": "trial", "amount_usd": 299},
    ))
    bus.publish(Event(
        type="subscription.cancellation_requested",
        venture_id="postlineai",
        payload={"customer_id": "c1"},
    ))

    assert len(cancelled) == 1
    assert cancelled[0].payload["status"] == "cancelled"
