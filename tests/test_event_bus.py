from flywheel.core.events import Event, InMemoryEventBus


def _evt(type: str = "thing.happened") -> Event:
    return Event(type=type, venture_id="v1")


def test_publish_delivers_to_exact_type_subscribers() -> None:
    bus = InMemoryEventBus()
    received: list[Event] = []
    bus.subscribe("thing.happened", received.append)

    bus.publish(_evt())

    assert len(received) == 1
    assert received[0].type == "thing.happened"


def test_non_matching_subscribers_not_called() -> None:
    bus = InMemoryEventBus()
    received: list[Event] = []
    bus.subscribe("other.thing", received.append)

    bus.publish(_evt())

    assert received == []


def test_wildcard_subscriber_sees_everything() -> None:
    bus = InMemoryEventBus()
    seen: list[str] = []
    bus.subscribe(InMemoryEventBus.WILDCARD, lambda e: seen.append(e.type))

    bus.publish(_evt("a.happened"))
    bus.publish(_evt("b.happened"))

    assert seen == ["a.happened", "b.happened"]


def test_child_inherits_venture_and_correlation() -> None:
    parent = _evt()
    child = parent.child("next.thing", {"k": "v"})

    assert child.venture_id == parent.venture_id
    assert child.correlation_id == parent.correlation_id
    assert child.event_id != parent.event_id
    assert child.payload == {"k": "v"}
