from __future__ import annotations

import io
import json

from duh.adapters.json_sink import JsonHudSink
from duh.models import HudCard, TranscriptEvent


def test_show_card_emits_jsonl_with_required_keys() -> None:
    buf = io.StringIO()
    sink = JsonHudSink(stream=buf)
    sink.show(
        HudCard(
            term="EBITDA",
            kind="acronym",
            blurb="Earnings before interest, taxes, depreciation, and amortization.",
            confidence=0.9,
            shown_at_ms=1200,
            ttl_ms=15_000,
        )
    )
    line = buf.getvalue().strip()
    assert "\n" not in line
    payload = json.loads(line)
    assert payload == {
        "type": "card",
        "term": "EBITDA",
        "kind": "acronym",
        "blurb": "Earnings before interest, taxes, depreciation, and amortization.",
        "confidence": 0.9,
        "shown_at_ms": 1200,
        "ttl_ms": 15_000,
    }


def test_show_transcript_and_status() -> None:
    buf = io.StringIO()
    sink = JsonHudSink(stream=buf)
    sink.status("capturing", device="BlackHole 2ch", index=0)
    sink.show_transcript(
        TranscriptEvent(id="e1", text="hello", is_final=True, t_ms=100, source="live")
    )
    lines = [json.loads(line) for line in buf.getvalue().strip().splitlines()]
    assert lines[0]["type"] == "status"
    assert lines[0]["message"] == "capturing"
    assert lines[0]["device"] == "BlackHole 2ch"
    assert lines[1]["type"] == "transcript"
    assert lines[1]["id"] == "e1"
    assert lines[1]["text"] == "hello"
    assert lines[1]["is_final"] is True
