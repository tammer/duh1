from __future__ import annotations

from duh.models import TermCandidate
from duh.ranker import Ranker


def _cand(term: str, confidence: float) -> TermCandidate:
    return TermCandidate(
        term=term,
        normalized=term.lower(),
        kind="jargon",
        confidence=confidence,
        event_id="e1",
        t_ms=0,
    )


def test_dedupes_normalized_terms() -> None:
    ranker = Ranker()
    first = ranker.consider(_cand("Microsoft", 0.9), "blurb", shown_at_ms=0)
    second = ranker.consider(_cand("microsoft", 0.95), "blurb", shown_at_ms=100)
    assert first is not None
    assert second is None
    assert len(ranker.visible) == 1


def test_rejects_below_min_confidence() -> None:
    ranker = Ranker(min_confidence=0.6)
    assert ranker.consider(_cand("x", 0.5), "blurb", shown_at_ms=0) is None


def test_max_visible_drops_lowest_confidence() -> None:
    ranker = Ranker(max_visible=3)
    assert ranker.consider(_cand("a", 0.9), "a", 0) is not None
    assert ranker.consider(_cand("b", 0.8), "b", 0) is not None
    assert ranker.consider(_cand("c", 0.7), "c", 0) is not None
    dropped = ranker.consider(_cand("d", 0.65), "d", 0)
    assert dropped is None
    assert {c.term for c in ranker.visible} == {"a", "b", "c"}


def test_higher_confidence_can_enter_when_over_cap() -> None:
    ranker = Ranker(max_visible=2)
    ranker.consider(_cand("a", 0.7), "a", 0)
    ranker.consider(_cand("b", 0.8), "b", 0)
    entered = ranker.consider(_cand("c", 0.95), "c", 0)
    assert entered is not None
    assert {c.term for c in ranker.visible} == {"b", "c"}
