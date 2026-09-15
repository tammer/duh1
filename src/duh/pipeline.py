from __future__ import annotations

from collections.abc import Callable

from duh.clock import SystemClock
from duh.detector import TermDetector
from duh.llm_analyzer import GroqUtteranceAnalyzer
from duh.models import TermCandidate, TranscriptEvent
from duh.ports import Clock, Enricher, HudSink, TranscriptSource
from duh.ranker import Ranker
from duh.timing import Stopwatch, log_timing


class CallPipeline:
    """Detect → enrich → rank → sink, or LLM analyze → rank → sink."""

    def __init__(
        self,
        *,
        detector: TermDetector | None = None,
        enricher: Enricher | None = None,
        analyzer: GroqUtteranceAnalyzer | None = None,
        sink: HudSink,
        ranker: Ranker | None = None,
        clock: Clock | None = None,
        on_event: Callable[[TranscriptEvent], None] | None = None,
    ) -> None:
        if analyzer is None and enricher is None:
            raise ValueError("CallPipeline requires enricher (mock) or analyzer (groq)")
        self.detector = detector or TermDetector()
        self.enricher = enricher
        self.analyzer = analyzer
        self.sink = sink
        self.ranker = ranker or Ranker()
        self.clock = clock or SystemClock()
        self.on_event = on_event

    def handle_event(self, event: TranscriptEvent) -> None:
        sw = Stopwatch()
        if self.on_event is not None:
            self.on_event(event)

        cards_shown = 0
        if self.analyzer is not None:
            cards_shown = self._handle_with_analyzer(event)
        else:
            assert self.enricher is not None
            cards_shown = self._handle_with_enricher(event)

        log_timing(
            "pipeline",
            event_id=event.id,
            pipeline_ms=sw.ms(),
            cards=cards_shown,
            source=event.source,
        )

    def _handle_with_enricher(self, event: TranscriptEvent) -> int:
        assert self.enricher is not None
        cards_shown = 0
        for candidate in self.detector.detect(event):
            blurb = self.enricher.enrich(candidate.term, candidate.kind)
            if blurb is None:
                continue
            card = self.ranker.consider(
                candidate,
                blurb,
                shown_at_ms=event.t_ms,
            )
            if card is not None:
                self.sink.show(card)
                cards_shown += 1
                log_timing(
                    "card",
                    event_id=event.id,
                    term=card.term,
                    kind=card.kind,
                )
        return cards_shown

    def _handle_with_analyzer(self, event: TranscriptEvent) -> int:
        assert self.analyzer is not None
        cards_shown = 0
        for analyzed in self.analyzer.analyze(event):
            candidate = TermCandidate(
                term=analyzed.term,
                normalized=analyzed.term.lower(),
                kind=analyzed.kind,
                confidence=analyzed.confidence,
                event_id=event.id,
                t_ms=event.t_ms,
            )
            card = self.ranker.consider(
                candidate,
                analyzed.blurb,
                shown_at_ms=event.t_ms,
            )
            if card is not None:
                self.sink.show(card)
                cards_shown += 1
                log_timing(
                    "card",
                    event_id=event.id,
                    term=card.term,
                    kind=card.kind,
                )
        return cards_shown

    def run(self, source: TranscriptSource) -> None:
        for event in source.events():
            self.handle_event(event)
