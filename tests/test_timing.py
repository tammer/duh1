from __future__ import annotations

from duh.timing import Stopwatch, log_timing, timing_enabled


def test_timing_disabled(monkeypatch, capsys) -> None:
    monkeypatch.setenv("DUH_TIMING", "0")
    monkeypatch.delenv("DUH_TIMING_LOG", raising=False)
    assert timing_enabled() is False
    log_timing("stt", stt_ms=12.3)
    assert capsys.readouterr().err == ""


def test_timing_logs_to_stderr_and_file(monkeypatch, tmp_path, capsys) -> None:
    log_path = tmp_path / "timing.log"
    monkeypatch.setenv("DUH_TIMING", "1")
    monkeypatch.setenv("DUH_TIMING_LOG", str(log_path))
    log_timing("stt", event_id="e1", stt_ms=12.34, chars=10)
    err = capsys.readouterr().err
    assert "[duh.timing] stt" in err
    assert "event_id=e1" in err
    assert "stt_ms=12.3" in err
    assert log_path.read_text(encoding="utf-8").strip() == err.strip()


def test_stopwatch_advances() -> None:
    sw = Stopwatch()
    assert sw.ms() >= 0.0
