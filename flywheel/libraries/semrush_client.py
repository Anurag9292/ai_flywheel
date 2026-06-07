"""``semrush-client`` — derived in PostlineAI Step 2.

A **library tool** (leaf I/O) wrapping the SEMrush API for keyword /
search-volume data. Pure function calls; no events.

Fake-first per ``new_docs/stack.md``; the real impl swaps in behind the
``SemrushClient`` Protocol when desk research needs live volume data.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class KeywordVolume(BaseModel):
    keyword: str
    monthly_volume: int
    competition: float  # 0.0 (low) .. 1.0 (high)


@runtime_checkable
class SemrushClient(Protocol):
    def keyword_volume(self, keywords: list[str]) -> list[KeywordVolume]: ...


class FakeSemrushClient:
    """Offline SEMrush client returning deterministic canned volumes.

    Unknown keywords get a stable pseudo-volume derived from the keyword text,
    so output is reproducible without a fixture for every term.
    """

    def __init__(self, fixtures: dict[str, KeywordVolume] | None = None) -> None:
        self._fixtures = fixtures or {}

    def keyword_volume(self, keywords: list[str]) -> list[KeywordVolume]:
        out: list[KeywordVolume] = []
        for kw in keywords:
            if kw in self._fixtures:
                out.append(self._fixtures[kw])
                continue
            # Deterministic pseudo-volume from a stable hash of the keyword.
            seed = sum(ord(c) for c in kw)
            out.append(
                KeywordVolume(
                    keyword=kw,
                    monthly_volume=(seed * 37) % 50_000,
                    competition=round((seed % 100) / 100, 2),
                )
            )
        return out
