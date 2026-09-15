from __future__ import annotations

from types import SimpleNamespace

import groq
import pytest

from duh.groq_client import GroqClient, get_groq_stt_model


def test_get_groq_stt_model_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_STT_MODEL", raising=False)
    assert get_groq_stt_model() == "whisper-large-v3-turbo"


def test_get_groq_stt_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_STT_MODEL", "whisper-large-v3")
    assert get_groq_stt_model() == "whisper-large-v3"


def test_transcribe_wav(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeTranscriptions:
        def create(self, **kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(text="  hello world  ")

    class FakeGroq:
        def __init__(self, *, api_key: str) -> None:
            captured["api_key"] = api_key
            self.audio = SimpleNamespace(transcriptions=FakeTranscriptions())

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
    monkeypatch.setattr(groq, "Groq", FakeGroq)

    client = GroqClient()
    assert client.transcribe_wav(b"RIFF") == "hello world"
    assert captured["api_key"] == "test-key"
    assert captured["model"] == "whisper-large-v3-turbo"
    assert captured["language"] == "en"
    assert captured["file"] == ("chunk.wav", b"RIFF", "audio/wav")


def test_transcribe_wav_empty_text(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeGroq:
        def __init__(self, *, api_key: str) -> None:
            self.audio = SimpleNamespace(
                transcriptions=SimpleNamespace(
                    create=lambda **kwargs: SimpleNamespace(text=None)
                )
            )

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(groq, "Groq", FakeGroq)
    assert GroqClient().transcribe_wav(b"x") == ""
