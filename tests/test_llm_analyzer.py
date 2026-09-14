from __future__ import annotations

from typing import Any

from duh.cache import TermCache
from duh.llm_analyzer import GroqUtteranceAnalyzer
from duh.models import TranscriptEvent


class FakeChatClient:
    """Deterministic ChatClient for tests."""

    def __init__(self, responses: list[Any] | None = None) -> None:
        self.responses = list(responses or [])
        self.calls: list[tuple[str, str]] = []

    def chat_json(self, system: str, user: str) -> Any:
        self.calls.append((system, user))
        if not self.responses:
            return []
        return self.responses.pop(0)


def test_analyzer_parses_terms_and_caches(tmp_path) -> None:
    cache = TermCache(tmp_path / "enrichments.json")
    client = FakeChatClient(
        [
            [
                {
                    "term": "backwardation",
                    "kind": "jargon",
                    "blurb": "Futures curve where near contracts price above later ones.",
                    "confidence": 0.9,
                }
            ]
        ]
    )
    analyzer = GroqUtteranceAnalyzer(client, cache=cache)
    event = TranscriptEvent(
        id="e1",
        text="It's a backwardation market.",
        is_final=True,
        t_ms=0,
    )
    terms = analyzer.analyze(event)
    assert len(terms) == 1
    assert terms[0].term == "backwardation"
    assert cache.get("backwardation") is not None
    assert cache.get("backwardation")["blurb"].startswith("Futures")


def test_analyzer_skips_partials() -> None:
    client = FakeChatClient([[{"term": "x", "kind": "other", "blurb": "y", "confidence": 1}]])
    analyzer = GroqUtteranceAnalyzer(client, cache=TermCache())
    terms = analyzer.analyze(
        TranscriptEvent(id="e1", text="backwardation", is_final=False, t_ms=0)
    )
    assert terms == []
    assert client.calls == []


def test_analyzer_session_already_known_passed_and_deduped(tmp_path) -> None:
    cache = TermCache(tmp_path / "c.json")
    client = FakeChatClient(
        [
            [
                {
                    "term": "contango",
                    "kind": "jargon",
                    "blurb": "Later contracts richer than near.",
                    "confidence": 0.9,
                }
            ],
            [],  # second call should see already_known
        ]
    )
    analyzer = GroqUtteranceAnalyzer(client, cache=cache)
    e1 = TranscriptEvent(id="e1", text="Oil is in contango.", is_final=True, t_ms=0)
    e2 = TranscriptEvent(id="e2", text="Still contango into winter.", is_final=True, t_ms=1)
    assert len(analyzer.analyze(e1)) == 1
    assert analyzer.analyze(e2) == []
    import json

    second_user = json.loads(client.calls[1][1])
    assert "contango" in second_user["already_known"]


def test_analyzer_prefers_disk_cache_blurb(tmp_path) -> None:
    cache = TermCache(tmp_path / "c.json")
    cache.put("ARR", kind="acronym", blurb="Cached ARR blurb.")
    client = FakeChatClient(
        [
            [
                {
                    "term": "ARR",
                    "kind": "acronym",
                    "blurb": "Model-generated blurb that should be ignored.",
                    "confidence": 0.7,
                }
            ]
        ]
    )
    analyzer = GroqUtteranceAnalyzer(client, cache=cache)
    terms = analyzer.analyze(
        TranscriptEvent(id="e1", text="Our ARR is up.", is_final=True, t_ms=0)
    )
    assert terms[0].blurb == "Cached ARR blurb."


def test_analyzer_tolerates_wrapped_json(tmp_path) -> None:
    cache = TermCache(tmp_path / "c.json")
    client = FakeChatClient(
        [{"terms": [{"term": "Stripe", "kind": "company", "blurb": "Payments API.", "confidence": 0.8}]}]
    )
    analyzer = GroqUtteranceAnalyzer(client, cache=cache)
    terms = analyzer.analyze(
        TranscriptEvent(id="e1", text="Stripe handles it.", is_final=True, t_ms=0)
    )
    assert [t.term for t in terms] == ["Stripe"]


def test_term_cache_roundtrip(tmp_path) -> None:
    path = tmp_path / "enrichments.json"
    cache = TermCache(path)
    cache.put("swaption", kind="jargon", blurb="Option on a swap.")
    reloaded = TermCache(path)
    assert reloaded.get("SWAPTION")["blurb"] == "Option on a swap."
    assert "swaption" in reloaded.known_terms()


def test_parse_json_content_fences() -> None:
    from duh.groq_client import parse_json_content

    assert parse_json_content('```json\n[{"a": 1}]\n```') == [{"a": 1}]


def test_pipeline_analyzer_path(tmp_path) -> None:
    from duh.adapters.memory_sink import InMemoryHudSink
    from duh.pipeline import CallPipeline
    from duh.ranker import Ranker

    cache = TermCache(tmp_path / "c.json")
    client = FakeChatClient(
        [
            [
                {
                    "term": "backwardation",
                    "kind": "jargon",
                    "blurb": "Near over far in futures.",
                    "confidence": 0.95,
                }
            ]
        ]
    )
    sink = InMemoryHudSink()
    pipeline = CallPipeline(
        analyzer=GroqUtteranceAnalyzer(client, cache=cache),
        sink=sink,
        ranker=Ranker(max_visible=10),
    )
    pipeline.handle_event(
        TranscriptEvent(
            id="e1",
            text="It's a backwardation market.",
            is_final=True,
            t_ms=100,
        )
    )
    assert sink.terms == ["backwardation"]
