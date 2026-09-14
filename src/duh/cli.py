from __future__ import annotations

import argparse
import sys
from pathlib import Path

from duh.adapters.fixture_source import FixtureReplaySource
from duh.adapters.terminal_sink import TerminalHudSink
from duh.enricher import CachingEnricher, MockEnricher
from duh.pipeline import CallPipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="duh-replay",
        description="Replay a call fixture through the meeting HUD pipeline.",
    )
    parser.add_argument(
        "fixture",
        type=Path,
        help="Path to a call fixture JSON file",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=0.0,
        help="Playback speed (0 = as fast as possible, 1 = realtime, 4 = 4x)",
    )
    parser.add_argument(
        "--enrichments",
        type=Path,
        default=None,
        help="Optional path to enrichments.json (defaults to packaged fixtures)",
    )
    args = parser.parse_args(argv)

    if not args.fixture.is_file():
        print(f"error: fixture not found: {args.fixture}", file=sys.stderr)
        return 1

    source = FixtureReplaySource.from_path(args.fixture, speed=args.speed)
    enricher = CachingEnricher(MockEnricher(args.enrichments))
    sink = TerminalHudSink()
    pipeline = CallPipeline(
        enricher=enricher,
        sink=sink,
        on_event=sink.show_transcript,
    )
    pipeline.run(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
