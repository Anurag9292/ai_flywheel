from flywheel.libraries.email_client import FakeEmailClient
from flywheel.libraries.slack_client import FakeSlackClient


def test_fake_slack_records_messages() -> None:
    client = FakeSlackClient()
    msg = client.post_message("#ventures", "hello")
    assert msg.channel == "#ventures"
    assert client.sent == [msg]


def test_fake_email_records_messages() -> None:
    client = FakeEmailClient()
    msg = client.send("founder@example.com", "subj", "body")
    assert msg.to == "founder@example.com"
    assert client.sent[0].subject == "subj"
