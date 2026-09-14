from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterator
from pathlib import Path

from duh.models import TranscriptEvent

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE_RE = re.compile(r"\s+")

PARTIAL_STEP_MS = 400
FINAL_STEP_MS = 800


def normalize_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def split_sentences(text: str) -> list[str]:
    """Split on .?! followed by whitespace; keep trailing unterminated text."""
    text = normalize_whitespace(text)
    if not text:
        return []
    parts = _SENTENCE_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def chunk_sentence_events(
    sentence: str,
    *,
    words: int,
    start_id: int,
    start_t_ms: int,
) -> tuple[list[TranscriptEvent], int, int]:
    """
    Emit growing partials every `words` tokens, then one final.

    Returns (events, next_id, next_t_ms).
    """
    tokens = sentence.split(" ")
    if not tokens or words < 1:
        words = max(1, words)

    events: list[TranscriptEvent] = []
    event_id = start_id
    t_ms = start_t_ms

    # Partials at words, 2*words, ... strictly before the full sentence.
    for end in range(words, len(tokens), words):
        partial = " ".join(tokens[:end])
        events.append(
            TranscriptEvent(
                id=f"e{event_id}",
                text=partial,
                is_final=False,
                t_ms=t_ms,
                source="fixture",
            )
        )
        event_id += 1
        t_ms += PARTIAL_STEP_MS

    events.append(
        TranscriptEvent(
            id=f"e{event_id}",
            text=sentence,
            is_final=True,
            t_ms=t_ms,
            source="fixture",
        )
    )
    event_id += 1
    t_ms += FINAL_STEP_MS
    return events, event_id, t_ms


class PlainTextStreamSource:
    """Replay a plain-text transcript as STT-like partials + finals."""

    def __init__(
        self,
        text: str,
        *,
        words: int = 8,
        speed: float = 0.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.text = text
        self.words = max(1, words)
        self.speed = speed
        self._sleep = sleep

    @classmethod
    def from_path(
        cls,
        path: Path | str,
        *,
        words: int = 8,
        speed: float = 0.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> PlainTextStreamSource:
        path = Path(path)
        return cls(
            path.read_text(encoding="utf-8"),
            words=words,
            speed=speed,
            sleep=sleep,
        )

    def events(self) -> Iterator[TranscriptEvent]:
        sentences = split_sentences(self.text)
        event_id = 1
        t_ms = 0
        last_t: int | None = None

        for sentence in sentences:
            batch, event_id, t_ms = chunk_sentence_events(
                sentence,
                words=self.words,
                start_id=event_id,
                start_t_ms=t_ms,
            )
            for event in batch:
                if self.speed > 0 and last_t is not None:
                    delta_ms = max(0, event.t_ms - last_t)
                    self._sleep((delta_ms / 1000.0) / self.speed)
                last_t = event.t_ms
                yield event
