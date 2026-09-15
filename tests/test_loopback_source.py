from __future__ import annotations

import math
import pytest

from duh.adapters.loopback_source import (
    LiveLoopbackSource,
    as_mono_floats,
    get_capture_device,
    is_microphone_device,
    resolve_input_device,
)
from duh.audio_chunker import SAMPLE_RATE, SpeechChunker
from duh.clock import FakeClock


def _sine(seconds: float, *, amp: float = 0.2) -> list[float]:
    n = int(seconds * SAMPLE_RATE)
    return [amp * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE) for i in range(n)]


def test_is_microphone_device() -> None:
    assert is_microphone_device("MacBook Pro Microphone") is True
    assert is_microphone_device("Built-in Microphone") is True
    assert is_microphone_device("USB Mic") is True
    assert is_microphone_device("BlackHole 2ch") is False
    assert is_microphone_device("Microsoft Teams Audio") is False


def test_get_capture_device(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DUH_CAPTURE_DEVICE", raising=False)
    assert get_capture_device() is None
    monkeypatch.setenv("DUH_CAPTURE_DEVICE", "BlackHole 2ch")
    assert get_capture_device() == "BlackHole 2ch"


def test_resolve_refuses_mic_spec() -> None:
    with pytest.raises(ValueError, match="refusing microphone"):
        resolve_input_device("Built-in Microphone")


def test_resolve_refuses_mic_index(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "duh.adapters.loopback_source.list_input_devices",
        lambda: [(0, "BlackHole 2ch"), (1, "MacBook Pro Microphone")],
    )
    with pytest.raises(ValueError, match="refusing microphone"):
        resolve_input_device("1")
    assert resolve_input_device("0") == (0, "BlackHole 2ch")
    assert resolve_input_device("BlackHole") == (0, "BlackHole 2ch")


def test_as_mono_floats_mixes_stereo_rows() -> None:
    assert as_mono_floats([[0.0, 1.0], [0.5, 0.5]]) == [0.5, 0.5]
    assert as_mono_floats([0.25, -0.5]) == [0.25, -0.5]


def test_live_source_emits_final_live_events() -> None:
    calls: list[bytes] = []

    def transcribe(wav: bytes) -> str:
        calls.append(wav)
        return "  swaption on the 10-year  "

    source = LiveLoopbackSource(
        transcribe=transcribe,
        frames=iter([_sine(0.6)]),
        chunker=SpeechChunker(),
        clock=FakeClock(0),
    )
    events = list(source.events())
    assert len(events) == 1
    assert len(calls) == 1
    event = events[0]
    assert event.source == "live"
    assert event.is_final is True
    assert event.text == "swaption on the 10-year"
    assert event.id == "e1"
    assert event.t_ms == 0


def test_live_source_drops_empty_transcripts() -> None:
    source = LiveLoopbackSource(
        transcribe=lambda wav: "   ",
        frames=iter([_sine(0.6)]),
        clock=FakeClock(0),
    )
    assert list(source.events()) == []


def test_live_source_requires_device_or_frames() -> None:
    with pytest.raises(ValueError, match="device or injected frames"):
        LiveLoopbackSource(transcribe=lambda wav: "x")
