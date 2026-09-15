from __future__ import annotations

import io
import math
import wave
from array import array
from collections.abc import Sequence

SAMPLE_RATE = 16_000
ENERGY_THRESHOLD = 0.01
SILENCE_FLUSH_MS = 1_000
MAX_SPEECH_MS = 8_000
MIN_SPEECH_MS = 400


def rms(samples: Sequence[float]) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(float(x) * float(x) for x in samples) / len(samples))


def duration_ms(n_samples: int, sample_rate: int = SAMPLE_RATE) -> int:
    if sample_rate <= 0:
        return 0
    return int(n_samples * 1000 / sample_rate)


def pcm_to_wav_bytes(
    samples: Sequence[float],
    *,
    sample_rate: int = SAMPLE_RATE,
) -> bytes:
    """Encode float PCM in [-1, 1] as a mono 16-bit WAV blob."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        pcm = array("h")
        for x in samples:
            v = max(-1.0, min(1.0, float(x)))
            pcm.append(int(v * 32767.0))
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


class SpeechChunker:
    """RMS energy gate: flush after trailing silence or a max speech duration."""

    def __init__(
        self,
        *,
        sample_rate: int = SAMPLE_RATE,
        energy_threshold: float = ENERGY_THRESHOLD,
        silence_flush_ms: int = SILENCE_FLUSH_MS,
        max_speech_ms: int = MAX_SPEECH_MS,
        min_speech_ms: int = MIN_SPEECH_MS,
    ) -> None:
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.silence_flush_ms = silence_flush_ms
        self.max_speech_ms = max_speech_ms
        self.min_speech_ms = min_speech_ms
        self._buffer: list[float] = []
        self._speech_samples = 0
        self._silence_samples = 0
        self._in_speech = False

    def push(self, frame: Sequence[float]) -> bytes | None:
        if not frame:
            return None
        samples = [float(x) for x in frame]
        if rms(samples) >= self.energy_threshold:
            self._in_speech = True
            self._buffer.extend(samples)
            self._speech_samples += len(samples)
            self._silence_samples = 0
            if duration_ms(self._speech_samples, self.sample_rate) >= self.max_speech_ms:
                return self._emit_if_long_enough(force=True)
            return None

        if not self._in_speech:
            return None

        self._buffer.extend(samples)
        self._silence_samples += len(samples)
        if duration_ms(self._silence_samples, self.sample_rate) >= self.silence_flush_ms:
            return self._emit_if_long_enough(force=False)
        return None

    def flush(self) -> bytes | None:
        if not self._in_speech:
            self._reset()
            return None
        return self._emit_if_long_enough(force=False)

    def _emit_if_long_enough(self, *, force: bool) -> bytes | None:
        speech_ms = duration_ms(self._speech_samples, self.sample_rate)
        samples = self._buffer
        self._reset()
        if not samples:
            return None
        if not force and speech_ms < self.min_speech_ms:
            return None
        return pcm_to_wav_bytes(samples, sample_rate=self.sample_rate)

    def _reset(self) -> None:
        self._buffer = []
        self._speech_samples = 0
        self._silence_samples = 0
        self._in_speech = False
