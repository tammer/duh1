from __future__ import annotations

from typing import Iterator, Protocol

from duh.models import HudCard, TermKind, TranscriptEvent


class TranscriptSource(Protocol):
    def events(self) -> Iterator[TranscriptEvent]:
        """Yield transcript events in timeline order."""


class Enricher(Protocol):
    def enrich(self, term: str, kind: TermKind) -> str | None:
        """Return a short blurb, or None if unknown."""


class HudSink(Protocol):
    def show(self, card: HudCard) -> None:
        """Present a HUD card."""

    def clear(self) -> None:
        """Clear visible cards."""


class Clock(Protocol):
    def now_ms(self) -> int:
        """Current time in milliseconds."""
