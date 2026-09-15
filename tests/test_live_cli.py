from __future__ import annotations

import pytest

from duh.live_cli import main


def test_live_cli_requires_device(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("duh.live_cli._load_dotenv", lambda: None)
    monkeypatch.delenv("DUH_CAPTURE_DEVICE", raising=False)
    assert main([]) == 1
    err = capsys.readouterr().err
    assert "--device" in err
    assert "microphone" in err.lower()


def test_live_cli_refuses_microphone(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("duh.live_cli._load_dotenv", lambda: None)
    assert main(["--device", "Built-in Microphone"]) == 1
    assert "refusing microphone" in capsys.readouterr().err


def test_live_cli_requires_api_key(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("duh.live_cli._load_dotenv", lambda: None)
    monkeypatch.setattr("duh.live_cli.get_groq_api_key", lambda: None)
    assert main(["--device", "BlackHole 2ch"]) == 1
    assert "GROQ_API_KEY" in capsys.readouterr().err


def test_live_cli_list_devices_without_sounddevice(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("duh.live_cli._load_dotenv", lambda: None)

    def boom() -> list[tuple[int, str]]:
        raise ImportError('sounddevice is required for live capture; install with pip install -e ".[live]"')

    monkeypatch.setattr("duh.live_cli.list_input_devices", boom)
    assert main(["--list-devices"]) == 1
    err = capsys.readouterr().err
    assert "sounddevice" in err
    assert "[live]" in err
