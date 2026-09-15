from __future__ import annotations

import io
import os
import queue
import re
import wave
from collections.abc import Callable, Iterator, Sequence
from typing import Any

from duh.audio_chunker import SAMPLE_RATE, SpeechChunker
from duh.clock import SystemClock
from duh.models import TranscriptEvent
from duh.ports import Clock
from duh.timing import Stopwatch, log_timing

TranscribeFn = Callable[[bytes], str]

_MIC_NAME_RE = re.compile(r"\b(mic|microphone|built-in)\b", re.IGNORECASE)

LIVE_EXTRA_HINT = 'pip install -e ".[live]"'


def get_capture_device() -> str | None:
    value = os.environ.get("DUH_CAPTURE_DEVICE", "").strip()
    return value or None


def is_microphone_device(name: str) -> bool:
    return bool(_MIC_NAME_RE.search(name.strip()))


def _import_sounddevice() -> Any:
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise ImportError(
            f"sounddevice is required for live capture; install with {LIVE_EXTRA_HINT}"
        ) from exc
    return sd


def list_input_devices() -> list[tuple[int, str]]:
    sd = _import_sounddevice()
    devices = sd.query_devices()
    out: list[tuple[int, str]] = []
    for index, info in enumerate(devices):
        if int(info.get("max_input_channels") or 0) > 0:
            out.append((index, str(info["name"])))
    return out


def resolve_input_device(spec: str) -> tuple[int, str]:
    """Resolve a name substring or numeric index to (index, name). Refuses mics."""
    spec = spec.strip()
    if not spec:
        raise ValueError("capture device is required")
    if is_microphone_device(spec):
        raise ValueError(f"refusing microphone device: {spec}")

    devices = list_input_devices()
    if spec.isdigit():
        index = int(spec)
        for device_index, name in devices:
            if device_index == index:
                if is_microphone_device(name):
                    raise ValueError(f"refusing microphone device: {name}")
                return device_index, name
        raise ValueError(f"no input device with index {index}")

    matches = [
        (device_index, name)
        for device_index, name in devices
        if spec.lower() in name.lower()
    ]
    if not matches:
        raise ValueError(f"no input device matching {spec!r}")
    exact = [
        (device_index, name)
        for device_index, name in matches
        if name.lower() == spec.lower()
    ]
    if len(exact) == 1:
        matches = exact
    elif len(matches) > 1:
        listed = ", ".join(f"{i}:{name}" for i, name in matches)
        raise ValueError(f"ambiguous device {spec!r}: {listed}")
    index, name = matches[0]
    if is_microphone_device(name):
        raise ValueError(f"refusing microphone device: {name}")
    return index, name


def as_mono_floats(frame: Any) -> list[float]:
    """Mix a PortAudio/numpy frame down to mono float samples."""
    ndim = getattr(frame, "ndim", None)
    if ndim == 2:
        return [float(x) for x in frame.mean(axis=1)]
    if ndim == 1:
        return [float(x) for x in frame]
    if not frame:
        return []
    first = frame[0]
    if isinstance(first, (list, tuple)):
        return [sum(float(ch) for ch in row) / len(row) for row in frame]
    return [float(x) for x in frame]


class LiveLoopbackSource:
    """Capture loopback PCM, chunk on energy, transcribe, yield live events."""

    def __init__(
        self,
        *,
        transcribe: TranscribeFn,
        device: str | int | None = None,
        frames: Iterator[Sequence[float]] | None = None,
        chunker: SpeechChunker | None = None,
        clock: Clock | None = None,
        sample_rate: int = SAMPLE_RATE,
        blocksize: int = 1024,
    ) -> None:
        if frames is None and device is None:
            raise ValueError("LiveLoopbackSource requires device or injected frames")
        self.transcribe = transcribe
        self.device = None if device is None else str(device)
        self._frames = frames
        self.chunker = chunker or SpeechChunker(sample_rate=sample_rate)
        self.clock = clock or SystemClock()
        self.sample_rate = sample_rate
        self.blocksize = blocksize
        self.device_index: int | None = None
        self.device_name: str | None = None

    def events(self) -> Iterator[TranscriptEvent]:
        event_id = 1
        start_ms = self.clock.now_ms()
        frame_iter = self._iter_frames()
        try:
            try:
                for frame in frame_iter:
                    wav = self.chunker.push(frame)
                    event = self._event_from_wav(wav, event_id, start_ms)
                    if event is not None:
                        yield event
                        event_id += 1
            except KeyboardInterrupt:
                pass
            event = self._event_from_wav(self.chunker.flush(), event_id, start_ms)
            if event is not None:
                yield event
        finally:
            frame_iter.close()

    def _event_from_wav(
        self,
        wav: bytes | None,
        event_id: int,
        start_ms: int,
    ) -> TranscriptEvent | None:
        if not wav:
            return None
        eid = f"e{event_id}"
        audio_ms = _wav_duration_ms(wav)
        # Chunk is ready only after silence flush / max-speech; audio_ms is
        # buffered speech length (includes trailing silence samples in buffer).
        log_timing("chunk_ready", event_id=eid, audio_ms=audio_ms, wav_bytes=len(wav))
        sw = Stopwatch()
        text = (self.transcribe(wav) or "").strip()
        stt_ms = sw.ms()
        if not text:
            log_timing("stt", event_id=eid, audio_ms=audio_ms, stt_ms=stt_ms, empty=1)
            return None
        log_timing(
            "stt",
            event_id=eid,
            audio_ms=audio_ms,
            stt_ms=stt_ms,
            chars=len(text),
        )
        return TranscriptEvent(
            id=eid,
            text=text,
            is_final=True,
            t_ms=max(0, self.clock.now_ms() - start_ms),
            source="live",
        )

    def _iter_frames(self) -> Iterator[list[float]]:
        if self._frames is not None:
            yield from (as_mono_floats(frame) for frame in self._frames)
            return
        yield from self._iter_sounddevice_frames()

    def _iter_sounddevice_frames(self) -> Iterator[list[float]]:
        sd = _import_sounddevice()
        spec = self.device or ""
        self.device_index, self.device_name = resolve_input_device(spec)
        info = sd.query_devices(self.device_index, "input")
        channels = max(1, min(2, int(info.get("max_input_channels") or 1)))
        pending: queue.Queue[Any] = queue.Queue()

        def callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
            pending.put(indata.copy())

        with sd.InputStream(
            device=self.device_index,
            samplerate=self.sample_rate,
            channels=channels,
            dtype="float32",
            blocksize=self.blocksize,
            callback=callback,
        ):
            while True:
                try:
                    data = pending.get(timeout=0.25)
                except queue.Empty:
                    continue
                yield as_mono_floats(data)


def _wav_duration_ms(wav: bytes) -> int:
    try:
        with wave.open(io.BytesIO(wav), "rb") as wf:
            rate = wf.getframerate() or SAMPLE_RATE
            return int(wf.getnframes() * 1000 / rate)
    except wave.Error:
        return 0


__all__ = [
    "LIVE_EXTRA_HINT",
    "LiveLoopbackSource",
    "as_mono_floats",
    "get_capture_device",
    "is_microphone_device",
    "list_input_devices",
    "resolve_input_device",
]
