"""Tests for the event bus."""

import pytest

from ai_flywheel.core.events import Event, EventBus


@pytest.fixture
def event_bus():
    return EventBus()


async def test_publish_and_subscribe(event_bus: EventBus):
    """Events should be delivered to subscribers."""
    received = []

    async def handler(event: Event):
        received.append(event)

    event_bus.subscribe("test.event", handler)
    await event_bus.publish("test.event", "test_module", {"key": "value"})

    assert len(received) == 1
    assert received[0].event_type == "test.event"
    assert received[0].payload == {"key": "value"}


async def test_wildcard_subscription(event_bus: EventBus):
    """Wildcard subscriptions should match."""
    received = []

    async def handler(event: Event):
        received.append(event)

    event_bus.subscribe("agent.*", handler)
    await event_bus.publish("agent.completed", "agent_factory", {"id": "123"})

    assert len(received) == 1
    assert received[0].event_type == "agent.completed"


async def test_global_wildcard(event_bus: EventBus):
    """Global wildcard should receive all events."""
    received = []

    async def handler(event: Event):
        received.append(event)

    event_bus.subscribe("*", handler)
    await event_bus.publish("anything.here", "any_module", {})

    assert len(received) == 1


async def test_no_matching_handlers(event_bus: EventBus):
    """Publishing with no subscribers should not error."""
    event = await event_bus.publish("unsubscribed.event", "module", {})
    assert event.event_type == "unsubscribed.event"


async def test_event_history(event_bus: EventBus):
    """Event history should be maintained."""
    await event_bus.publish("first", "mod", {"n": 1})
    await event_bus.publish("second", "mod", {"n": 2})

    history = event_bus.get_history()
    assert len(history) == 2
    assert history[0].payload == {"n": 1}
    assert history[1].payload == {"n": 2}


async def test_event_history_filtered(event_bus: EventBus):
    """Event history should be filterable."""
    await event_bus.publish("type_a", "mod", {}, venture_id="v1")
    await event_bus.publish("type_b", "mod", {}, venture_id="v2")
    await event_bus.publish("type_a", "mod", {}, venture_id="v1")

    history = event_bus.get_history(venture_id="v1")
    assert len(history) == 2


async def test_handler_error_doesnt_crash_bus(event_bus: EventBus):
    """Handler errors should be caught, not propagated."""
    async def bad_handler(event: Event):
        raise ValueError("intentional error")

    async def good_handler(event: Event):
        pass  # should still execute

    event_bus.subscribe("test", bad_handler)
    event_bus.subscribe("test", good_handler)

    # Should not raise
    await event_bus.publish("test", "mod", {})
