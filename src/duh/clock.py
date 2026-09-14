from __future__ import annotations

import time


class SystemClock:
    def now_ms(self) -> int:
        return int(time.time() * 1000)


class FakeClock:
    """Deterministic clock for tests; advance manually or via sleep helper."""

    def __init__(self, start_ms: int = 0) -> None:
        self._now_ms = start_ms

    def now_ms(self) -> int:
        return self._now_ms

    def advance(self, delta_ms: int) -> None:
        self._now_ms += delta_ms

    def set(self, ms: int) -> None:
        self._now_ms = ms
