"""``input-intake`` — derived in PostlineAI Step 5.

> *The venture needs to: collect raw input (voice notes / bullet points) from
> each customer on a cadence.*

An **event-driven node** that reacts to ``inbound.received``, normalizes the raw
input into a canonical record keyed by customer (transcribing audio via the
``transcription-client`` when needed), and emits ``input.captured``.

- **Reacts to:** ``inbound.received``.
- **Calls:** ``transcription-client`` (only when the input is audio).
- **Emits:** ``input.captured``.
- **Kind:** dumb (normalization, no LLM).
"""

from __future__ import annotations

from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.transcription_client import (
    FakeTranscriptionClient,
    TranscriptionClient,
)


class InputIntake:
    name = "input-intake"
    version = "0.1.0"
    kind = "dumb"
    reacts_to = ["inbound.received"]
    emits = ["input.captured"]
    calls = ["transcription-client"]

    def __init__(self, *, transcription: TranscriptionClient | None = None) -> None:
        self._transcription = transcription or FakeTranscriptionClient()

    def handle(self, event: Event, ctx: NodeContext) -> None:
        customer_id = event.payload.get("customer_id", "")
        kind = event.payload.get("kind", "text")
        content = event.payload.get("content", "")

        if kind == "audio":
            # Audio refs become text via the transcription library.
            text = self._transcription.transcribe(content).text
        else:
            text = content

        ctx.emit(
            type="input.captured",
            payload={"customer_id": customer_id, "text": text},
        )
