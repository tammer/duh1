from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from duh.models import HudCard, TranscriptEvent


class JsonHudSink:
    """Emit HUD events as JSONL on a stream (stdout by default)."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self.stream = stream if stream is not None else sys.stdout
        self._cards: list[HudCard] = []

    def emit(self, payload: dict[str, Any]) -> None:
        self.stream.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self.stream.flush()

    def status(self, message: str, **extra: Any) -> None:
        payload: dict[str, Any] = {"type": "status", "message": message}
        payload.update(extra)
        self.emit(payload)

    def error(self, message: str) -> None:
        self.emit({"type": "error", "message": message})

    def show_transcript(self, event: TranscriptEvent) -> None:
        self.emit(
            {
                "type": "transcript",
                "id": event.id,
                "text": event.text,
                "t_ms": event.t_ms,
                "is_final": event.is_final,
            }
        )

    def show(self, card: HudCard) -> None:
        self._cards.append(card)
        self._cards = self._cards[-3:]
        self.emit(
            {
                "type": "card",
                "term": card.term,
                "kind": card.kind,
                "blurb": card.blurb,
                "confidence": card.confidence,
                "shown_at_ms": card.shown_at_ms,
                "ttl_ms": card.ttl_ms,
            }
        )

    def clear(self) -> None:
        self._cards.clear()
        self.emit({"type": "clear"})
