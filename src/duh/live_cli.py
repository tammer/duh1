from __future__ import annotations

import argparse
import sys
from pathlib import Path

from duh.adapters.loopback_source import (
    LIVE_EXTRA_HINT,
    LiveLoopbackSource,
    get_capture_device,
    is_microphone_device,
    list_input_devices,
    resolve_input_device,
)
from duh.adapters.terminal_sink import TerminalHudSink
from duh.cache import TermCache
from duh.cli import _default_backend, _load_dotenv
from duh.enricher import CachingEnricher, MockEnricher
from duh.groq_client import GroqClient, get_groq_api_key
from duh.llm_analyzer import GroqUtteranceAnalyzer
from duh.models import TranscriptEvent
from duh.pipeline import CallPipeline


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(
        prog="duh-live",
        description=(
            "Capture Mac loopback audio (not the microphone), transcribe with "
            "Groq Whisper, and run the meeting HUD pipeline."
        ),
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Loopback input name or index (default: DUH_CAPTURE_DEVICE)",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="Print PortAudio input devices and exit",
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
    parser.add_argument(
        "--save-transcript",
        type=Path,
        default=None,
        help="Write final transcript lines to this .txt file",
    )
    args = parser.parse_args(argv)

    if args.list_devices:
        return _print_devices()

    device = (args.device or get_capture_device() or "").strip()
    if not device:
        print(
            "error: --device or DUH_CAPTURE_DEVICE is required "
            "(never defaults to the microphone)",
            file=sys.stderr,
        )
        return 1
    if is_microphone_device(device):
        print(f"error: refusing microphone device: {device}", file=sys.stderr)
        return 1

    if not get_groq_api_key():
        print("error: duh-live requires GROQ_API_KEY for Whisper STT", file=sys.stderr)
        return 1

    try:
        index, name = resolve_input_device(device)
    except ImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        client = GroqClient()
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    sink = TerminalHudSink()
    save_path: Path | None = args.save_transcript
    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text("", encoding="utf-8")

    def on_event(event: TranscriptEvent) -> None:
        sink.show_transcript(event)
        if save_path is not None and event.is_final and event.text.strip():
            with save_path.open("a", encoding="utf-8") as handle:
                handle.write(event.text.strip() + "\n")

    backend = args.backend or _default_backend()
    if backend == "groq":
        pipeline = CallPipeline(
            analyzer=GroqUtteranceAnalyzer(client, cache=TermCache(args.cache)),
            sink=sink,
            on_event=on_event,
        )
    else:
        pipeline = CallPipeline(
            enricher=CachingEnricher(MockEnricher(args.enrichments)),
            sink=sink,
            on_event=on_event,
        )

    source = LiveLoopbackSource(device=str(index), transcribe=client.transcribe_wav)
    print(
        f"capturing from {name} (index {index}) at 16 kHz mono. Ctrl+C to stop.",
        file=sys.stderr,
    )
    try:
        pipeline.run(source)
    except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr)
    return 0


def _print_devices() -> int:
    try:
        devices = list_input_devices()
    except ImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print(f"hint: {LIVE_EXTRA_HINT}", file=sys.stderr)
        return 1
    if not devices:
        print("no input devices found", file=sys.stderr)
        return 1
    for index, name in devices:
        marker = "  (refused: microphone)" if is_microphone_device(name) else ""
        print(f"{index}: {name}{marker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
