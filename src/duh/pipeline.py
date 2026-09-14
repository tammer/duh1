from __future__ import annotations

from collections.abc import Callable

from duh.clock import SystemClock
from duh.detector import TermDetector
from duh.models import TranscriptEvent
from duh.ports import Clock, Enricher, HudSink, TranscriptSource
from duh.ranker import Ranker


class CallPipeline:
    """Detect → enrich → rank → sink for each transcript event."""

    def __init__(
        self,
        *,
        detector: TermDetector | None = None,
        enricher: Enricher,
        sink: HudSink,
        ranker: Ranker | None = None,
        clock: Clock | None = None,
        on_event: Callable[[TranscriptEvent], None] | None = None,
    ) -> None:
        self.detector = detector or TermDetector()
        self.enricher = enricher
        self.sink = sink
        self.ranker = ranker or Ranker()
        self.clock = clock or SystemClock()
        self.on_event = on_event

    def handle_event(self, event: TranscriptEvent) -> None:
        if self.on_event is not None:
            self.on_event(event)

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

    def run(self, source: TranscriptSource) -> None:
        for event in source.events():
            self.handle_event(event)
