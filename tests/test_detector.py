from __future__ import annotations

from pathlib import Path

from duh.detector import TermDetector, load_lexicon
from duh.models import TranscriptEvent

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
LEXICON = load_lexicon(FIXTURES / "enrichments.json")


def _event(text: str, *, is_final: bool = True) -> TranscriptEvent:
    return TranscriptEvent(id="t1", text=text, is_final=is_final, t_ms=0)


def test_detects_jargon_from_lexicon() -> None:
    detector = TermDetector(LEXICON)
    terms = {c.normalized for c in detector.detect(_event("We priced a swaption today."))}
    assert "swaption" in terms


def test_detects_company_title_case() -> None:
    detector = TermDetector(LEXICON)
    terms = {c.term for c in detector.detect(_event("Microsoft is bidding."))}
    assert "Microsoft" in terms


def test_detects_acronym() -> None:
    detector = TermDetector(LEXICON)
    terms = {c.term for c in detector.detect(_event("Focus on EBITDA this quarter."))}
    assert "EBITDA" in terms


def test_ignores_partials() -> None:
    detector = TermDetector(LEXICON)
    assert detector.detect(_event("swaption", is_final=False)) == []


def test_ignores_denylisted_acronyms() -> None:
    detector = TermDetector(LEXICON)
    terms = {c.normalized for c in detector.detect(_event("OK CEO said ASAP."))}
    assert "ok" not in terms
    assert "ceo" not in terms
    assert "asap" not in terms


def test_skips_unknown_single_title_case() -> None:
    detector = TermDetector(LEXICON)
    terms = detector.detect(_event("Next slide please."))
    assert terms == []
