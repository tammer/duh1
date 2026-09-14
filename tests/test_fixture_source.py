from __future__ import annotations

from pathlib import Path

from duh.adapters.fixture_source import FixtureReplaySource
from duh.models import CallFixture, TranscriptEvent


def test_from_path_loads_events(tmp_path: Path) -> None:
    path = tmp_path / "call.json"
    path.write_text(
        CallFixture(
            name="t",
            events=[
                TranscriptEvent(id="e1", text="hi", t_ms=0),
                TranscriptEvent(id="e2", text="there", t_ms=1000),
            ],
        ).model_dump_json(),
        encoding="utf-8",
    )
    source = FixtureReplaySource.from_path(path, speed=0)
    events = list(source.events())
    assert [e.id for e in events] == ["e1", "e2"]


def test_speed_sleeps_scaled_deltas() -> None:
    sleeps: list[float] = []
    fixture = CallFixture(
        name="t",
        events=[
            TranscriptEvent(id="e1", text="a", t_ms=0),
            TranscriptEvent(id="e2", text="b", t_ms=4000),
            TranscriptEvent(id="e3", text="c", t_ms=6000),
        ],
    )
    source = FixtureReplaySource(
        fixture,
        speed=4.0,
        sleep=sleeps.append,
    )
    list(source.events())
    # deltas 4000ms and 2000ms at 4x => 1.0s and 0.5s
    assert sleeps == [1.0, 0.5]


def test_speed_zero_does_not_sleep() -> None:
    sleeps: list[float] = []
    fixture = CallFixture(
        name="t",
        events=[
            TranscriptEvent(id="e1", text="a", t_ms=0),
            TranscriptEvent(id="e2", text="b", t_ms=5000),
        ],
    )
    source = FixtureReplaySource(fixture, speed=0.0, sleep=sleeps.append)
    list(source.events())
    assert sleeps == []
