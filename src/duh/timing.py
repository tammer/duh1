from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any


def timing_enabled() -> bool:
    """Timing logs on by default; set DUH_TIMING=0 to disable."""
    value = os.environ.get("DUH_TIMING", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _timing_log_path() -> Path | None:
    """Optional file sink so the macOS app (which swallows stderr) can still be measured."""
    raw = os.environ.get("DUH_TIMING_LOG", "").strip()
    if raw:
        return Path(raw)
    # Default when enabled: repo-local file (worker cwd is normally repo root).
    if timing_enabled():
        return Path(".duh/timing.log")
    return None


def log_timing(stage: str, **fields: Any) -> None:
    """Print a single line: [duh.timing] stage key=value ... (stderr + .duh/timing.log)."""
    if not timing_enabled():
        return
    parts = [f"[duh.timing] {stage}"]
    for key, value in fields.items():
        if isinstance(value, float):
            parts.append(f"{key}={value:.1f}")
        else:
            parts.append(f"{key}={value}")
    line = " ".join(parts)
    print(line, file=sys.stderr, flush=True)
    path = _timing_log_path()
    if path is not None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            pass


class Stopwatch:
    """Simple perf_counter span helper."""

    def __init__(self) -> None:
        self._t0 = time.perf_counter()

    def ms(self) -> float:
        return (time.perf_counter() - self._t0) * 1000.0

    def reset(self) -> float:
        elapsed = self.ms()
        self._t0 = time.perf_counter()
        return elapsed
