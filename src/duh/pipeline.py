from __future__ import annotations

from collections.abc import Callable

from duh.clock import SystemClock
from duh.detector import TermDetector
from duh.llm_analyzer import GroqUtteranceAnalyzer
from duh.models import TermCandidate, TranscriptEvent
from duh.ports import Clock, Enricher, HudSink, TranscriptSource
from duh.ranker import Ranker


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
        if self.on_event is not None:
            self.on_event(event)

        if self.analyzer is not None:
            self._handle_with_analyzer(event)
            return

        assert self.enricher is not None
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

    def _handle_with_analyzer(self, event: TranscriptEvent) -> None:
        assert self.analyzer is not None
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

    def run(self, source: TranscriptSource) -> None:
        for event in source.events():
            self.handle_event(event)
