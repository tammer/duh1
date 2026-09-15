from __future__ import annotations

import json

import pytest

from duh.worker_cli import main


def test_worker_cli_requires_device(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("duh.worker_cli._load_dotenv", lambda: None)
    monkeypatch.delenv("DUH_CAPTURE_DEVICE", raising=False)
    assert main([]) == 1
    captured = capsys.readouterr()
    assert "--device" in captured.err
    err_event = json.loads(captured.out.strip().splitlines()[-1])
    assert err_event["type"] == "error"
    assert "microphone" in err_event["message"].lower()


def test_worker_cli_refuses_microphone(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("duh.worker_cli._load_dotenv", lambda: None)
    assert main(["--device", "Built-in Microphone"]) == 1
    captured = capsys.readouterr()
    assert "refusing microphone" in captured.err
    err_event = json.loads(captured.out.strip().splitlines()[-1])
    assert err_event["type"] == "error"


def test_worker_cli_requires_api_key(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("duh.worker_cli._load_dotenv", lambda: None)
    monkeypatch.setattr("duh.worker_cli.get_groq_api_key", lambda: None)
    assert main(["--device", "BlackHole 2ch"]) == 1
    captured = capsys.readouterr()
    assert "GROQ_API_KEY" in captured.err
    err_event = json.loads(captured.out.strip().splitlines()[-1])
    assert err_event["type"] == "error"
    assert "GROQ_API_KEY" in err_event["message"]
