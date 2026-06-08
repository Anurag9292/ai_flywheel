from flywheel.libraries.billing_client import FakeBillingClient
from flywheel.libraries.inbound_collector import FakeInboundCollector, InboundItem
from flywheel.libraries.linkedin_posting_client import FakeLinkedInPostingClient


def test_fake_inbound_drains_items_once() -> None:
    items = [
        InboundItem(customer_id="c1", kind="text", content="bullet points"),
        InboundItem(customer_id="c2", kind="audio", content="rec-1"),
    ]
    client = FakeInboundCollector(items=items)
    first = client.pull()
    assert [i.customer_id for i in first] == ["c1", "c2"]
    # Draining is one-shot.
    assert client.pull() == []


def test_fake_posting_records_published() -> None:
    client = FakeLinkedInPostingClient()
    post = client.publish("c1", "hello world")
    assert post.post_id == "li-post-1"
    assert post.customer_id == "c1"
    assert "li-post-1" in post.url
    assert client.published == [post]


def test_fake_billing_subscription_and_payment() -> None:
    client = FakeBillingClient()
    sub = client.create_subscription("c1", "pro", 299.0)
    assert sub.subscription_id == "sub-1"
    assert sub.status == "active"
    pay = client.capture_payment("c1", 299.0)
    assert pay.payment_id == "pay-1"
    assert pay.status == "captured"


def test_fake_billing_cancel() -> None:
    client = FakeBillingClient()
    sub = client.create_subscription("c1", "pro", 299.0)
    cancelled = client.cancel_subscription(sub.subscription_id)
    assert cancelled.status == "cancelled"
    # Unknown id returns a synthetic cancelled record, no raise.
    assert client.cancel_subscription("nope").status == "cancelled"
