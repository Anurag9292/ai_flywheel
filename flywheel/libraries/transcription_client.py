"""``transcription-client`` — derived in PostlineAI Step 3.

A **library tool** (leaf I/O) wrapping a speech-to-text API (Whisper / Deepgram)
used to turn recorded discovery calls into text. Pure function calls; no events.

Fake-first per ``new_docs/stack.md``; the real impl swaps in behind the
``TranscriptionClient`` Protocol when live audio must be transcribed.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class Transcript(BaseModel):
    audio_ref: str
    text: str


@runtime_checkable
class TranscriptionClient(Protocol):
    def transcribe(self, audio_ref: str) -> Transcript: ...


class FakeTranscriptionClient:
    """Offline transcription client returning deterministic canned text.

    Seeded with a small fixture so the ``pain-extractor`` node can run
    end-to-end. Unknown audio refs get a stable placeholder transcript.
    """

    def __init__(self, fixtures: dict[str, str] | None = None) -> None:
        self._fixtures = fixtures or {}

    def transcribe(self, audio_ref: str) -> Transcript:
        text = self._fixtures.get(
            audio_ref, f"Canned transcript for {audio_ref}."
        )
        return Transcript(audio_ref=audio_ref, text=text)
