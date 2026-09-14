from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from duh.adapters.fixture_source import FixtureReplaySource
from duh.adapters.terminal_sink import TerminalHudSink
from duh.cache import TermCache
from duh.enricher import CachingEnricher, MockEnricher
from duh.groq_client import GroqClient, get_groq_api_key
from duh.llm_analyzer import GroqUtteranceAnalyzer
from duh.pipeline import CallPipeline


def _load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE pairs from .env into os.environ (does not override)."""
    env_path = path or Path.cwd() / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def _default_backend() -> str:
    return "groq" if get_groq_api_key() else "mock"


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
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
        "--backend",
        choices=("mock", "groq"),
        default=None,
        help="Enrichment backend (default: groq if GROQ_API_KEY is set, else mock)",
    )
    parser.add_argument(
        "--enrichments",
        type=Path,
        default=None,
        help="Optional path to enrichments.json for --backend mock",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=None,
        help="Optional path to term cache JSON for --backend groq",
    )
    args = parser.parse_args(argv)

    if not args.fixture.is_file():
        print(f"error: fixture not found: {args.fixture}", file=sys.stderr)
        return 1

    backend = args.backend or _default_backend()
    source = FixtureReplaySource.from_path(args.fixture, speed=args.speed)
    sink = TerminalHudSink()

    if backend == "groq":
        if not get_groq_api_key():
            print(
                "error: --backend groq requires GROQ_API_KEY",
                file=sys.stderr,
            )
            return 1
        try:
            client = GroqClient()
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        analyzer = GroqUtteranceAnalyzer(client, cache=TermCache(args.cache))
        pipeline = CallPipeline(
            analyzer=analyzer,
            sink=sink,
            on_event=sink.show_transcript,
        )
    else:
        enricher = CachingEnricher(MockEnricher(args.enrichments))
        pipeline = CallPipeline(
            enricher=enricher,
            sink=sink,
            on_event=sink.show_transcript,
        )

    pipeline.run(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
