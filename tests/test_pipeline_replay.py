from __future__ import annotations

import json
from pathlib import Path

import pytest

from duh.adapters.fixture_source import FixtureReplaySource
from duh.adapters.memory_sink import InMemoryHudSink
from duh.detector import TermDetector, load_lexicon
from duh.enricher import CachingEnricher, MockEnricher
from duh.models import CallFixture
from duh.pipeline import CallPipeline
from duh.ranker import Ranker

ROOT = Path(__file__).resolve().parents[1]
CALLS = ROOT / "fixtures" / "calls"
ENRICHMENTS = ROOT / "fixtures" / "enrichments.json"


def _run_fixture(path: Path, *, max_visible: int = 10) -> tuple[CallFixture, InMemoryHudSink]:
    source = FixtureReplaySource.from_path(path, speed=0)
    sink = InMemoryHudSink()
    lexicon = load_lexicon(ENRICHMENTS)
    pipeline = CallPipeline(
        detector=TermDetector(lexicon),
        enricher=CachingEnricher(MockEnricher(ENRICHMENTS)),
        sink=sink,
        ranker=Ranker(max_visible=max_visible),
    )
    pipeline.run(source)
    return source.fixture, sink


@pytest.mark.parametrize(
    "filename",
    [
        "finance-jargon-basic.json",
        "company-mentions.json",
        "acronym-and-jargon.json",
        "false-positives.json",
        "dedupe-remention.json",
    ],
)
def test_golden_fixtures(filename: str) -> None:
    fixture, sink = _run_fixture(CALLS / filename)
    assert fixture.expect is not None

    shown_norm = {t.lower() for t in sink.terms}
    expected_norm = {t.lower() for t in fixture.expect.terms}
    assert shown_norm == expected_norm

    for banned in fixture.expect.must_not_show:
        assert banned.lower() not in shown_norm


def test_finance_fixture_file_parses() -> None:
    raw = json.loads((CALLS / "finance-jargon-basic.json").read_text(encoding="utf-8"))
    fixture = CallFixture.model_validate(raw)
    assert fixture.name == "finance-jargon-basic"
    assert len(fixture.events) >= 5
