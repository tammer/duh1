from __future__ import annotations

import io
import math
import wave

from duh.audio_chunker import (
    SAMPLE_RATE,
    SpeechChunker,
    duration_ms,
    pcm_to_wav_bytes,
    rms,
)


def _sine(seconds: float, *, amp: float = 0.2, sr: int = SAMPLE_RATE) -> list[float]:
    n = int(seconds * sr)
    return [amp * math.sin(2 * math.pi * 440 * i / sr) for i in range(n)]


def _silence(seconds: float, *, sr: int = SAMPLE_RATE) -> list[float]:
    return [0.0] * int(seconds * sr)


def _push_all(chunker: SpeechChunker, samples: list[float], size: int = 1024) -> list[bytes]:
    emitted: list[bytes] = []
    for start in range(0, len(samples), size):
        wav = chunker.push(samples[start : start + size])
        if wav is not None:
            emitted.append(wav)
    return emitted


def test_rms_empty_is_zero() -> None:
    assert rms([]) == 0.0


def test_rms_sine_above_threshold() -> None:
    assert rms(_sine(0.05)) > 0.01


def test_pcm_to_wav_bytes_is_mono_16k() -> None:
    wav = pcm_to_wav_bytes(_sine(0.1))
    with wave.open(io.BytesIO(wav), "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
        assert handle.getframerate() == SAMPLE_RATE
        assert handle.getnframes() == int(0.1 * SAMPLE_RATE)


def test_silence_stays_unflushed() -> None:
    chunker = SpeechChunker()
    emitted = _push_all(chunker, _silence(1.5))
    assert emitted == []
    assert chunker.flush() is None


def test_speech_plus_trailing_silence_emits_one_wav() -> None:
    chunker = SpeechChunker()
    emitted = _push_all(chunker, _sine(0.6) + _silence(0.5))
    assert len(emitted) == 1
    with wave.open(io.BytesIO(emitted[0]), "rb") as handle:
        assert handle.getnframes() > 0


def test_tiny_clip_is_discarded() -> None:
    chunker = SpeechChunker(min_speech_ms=400)
    emitted = _push_all(chunker, _sine(0.2) + _silence(0.5))
    assert emitted == []
    assert chunker.flush() is None


def test_default_max_speech_force_flush() -> None:
    """Defaults cap continuous speech so live HUD does not buffer ~8s."""
    from duh.audio_chunker import MAX_SPEECH_MS, SILENCE_FLUSH_MS

    assert SILENCE_FLUSH_MS == 400
    assert MAX_SPEECH_MS == 2_500
    chunker = SpeechChunker()
    emitted = _push_all(chunker, _sine(3.0))
    assert len(emitted) >= 1
    with wave.open(io.BytesIO(emitted[0]), "rb") as handle:
        # First force-flush should be around max_speech, not the full 3s.
        assert handle.getnframes() <= int(2.6 * SAMPLE_RATE)


def test_max_duration_force_flush() -> None:
    chunker = SpeechChunker(max_speech_ms=500, min_speech_ms=100)
    emitted = _push_all(chunker, _sine(0.7))
    assert len(emitted) == 1
    assert duration_ms(int(0.7 * SAMPLE_RATE)) >= 500


def test_end_flush_emits_remaining_speech() -> None:
    chunker = SpeechChunker()
    assert _push_all(chunker, _sine(0.6)) == []
    wav = chunker.flush()
    assert wav is not None
