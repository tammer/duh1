from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterator
from pathlib import Path

from duh.models import CallFixture, TranscriptEvent


class FixtureReplaySource:
    """Replay a CallFixture, optionally pacing by event timestamps."""

    def __init__(
        self,
        fixture: CallFixture,
        *,
        speed: float = 0.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """
        Args:
            fixture: Loaded call fixture.
            speed: Playback speed multiplier. 0 = as-fast-as-possible (no sleep).
                   1 = realtime, 4 = 4x, etc.
            sleep: Injectable sleep for tests.
        """
        self.fixture = fixture
        self.speed = speed
        self._sleep = sleep

    @classmethod
    def from_path(
        cls,
        path: Path | str,
        *,
        speed: float = 0.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> FixtureReplaySource:
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        fixture = CallFixture.model_validate(data)
        return cls(fixture, speed=speed, sleep=sleep)

    def events(self) -> Iterator[TranscriptEvent]:
        last_t: int | None = None
        for event in self.fixture.events:
            if self.speed > 0 and last_t is not None:
                delta_ms = max(0, event.t_ms - last_t)
                self._sleep((delta_ms / 1000.0) / self.speed)
            last_t = event.t_ms
            yield event
