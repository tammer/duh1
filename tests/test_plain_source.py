from __future__ import annotations

from duh.adapters.plain_source import (
    FINAL_STEP_MS,
    PARTIAL_STEP_MS,
    PlainTextStreamSource,
    chunk_sentence_events,
    split_sentences,
)


def test_split_sentences_multi() -> None:
    text = "Thank you. That's easier. Okay?"
    assert split_sentences(text) == ["Thank you.", "That's easier.", "Okay?"]


def test_split_sentences_trailing_unterminated() -> None:
    assert split_sentences("Hello world") == ["Hello world"]


def test_split_sentences_empty() -> None:
    assert split_sentences("   \n\n  ") == []


def test_chunk_partials_then_final_words_5() -> None:
    sentence = "We're looking at a swaption on the 10-year."
    events, next_id, next_t = chunk_sentence_events(
        sentence, words=5, start_id=1, start_t_ms=0
    )
    assert [e.is_final for e in events] == [False, True]
    assert events[0].text == "We're looking at a swaption"
    assert events[1].text == sentence
    assert events[0].t_ms == 0
    assert events[1].t_ms == PARTIAL_STEP_MS
    assert next_id == 3
    assert next_t == PARTIAL_STEP_MS + FINAL_STEP_MS


def test_short_sentence_is_single_final() -> None:
    events, _, _ = chunk_sentence_events("Thank you.", words=8, start_id=1, start_t_ms=0)
    assert len(events) == 1
    assert events[0].is_final is True
    assert events[0].text == "Thank you."


def test_plain_source_from_text_streams() -> None:
    source = PlainTextStreamSource(
        "Hello there friend. Second sentence here now yes.",
        words=3,
        speed=0,
    )
    events = list(source.events())
    assert any(not e.is_final for e in events)
    finals = [e for e in events if e.is_final]
    assert [e.text for e in finals] == [
        "Hello there friend.",
        "Second sentence here now yes.",
    ]


def test_plain_source_speed_sleeps() -> None:
    sleeps: list[float] = []
    source = PlainTextStreamSource(
        "One two three four five six.",
        words=3,
        speed=2.0,
        sleep=sleeps.append,
    )
    list(source.events())
    # partial at 0, final at 400ms → sleep 0.4/2 = 0.2
    assert sleeps == [0.2]


def test_plain_source_empty_yields_nothing() -> None:
    assert list(PlainTextStreamSource("  \n ").events()) == []


def test_from_path(tmp_path) -> None:
    path = tmp_path / "call.txt"
    path.write_text("Antler met Kinn today.", encoding="utf-8")
    events = list(PlainTextStreamSource.from_path(path, words=8).events())
    assert len(events) == 1
    assert events[0].is_final is True
    assert "Kinn" in events[0].text
