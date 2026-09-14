from __future__ import annotations

from duh.models import HudCard, TermCandidate


class Ranker:
    """Call-scoped dedupe, confidence floor, and max visible cards."""

    def __init__(
        self,
        *,
        min_confidence: float = 0.6,
        max_visible: int = 3,
        ttl_ms: int = 15_000,
    ) -> None:
        self.min_confidence = min_confidence
        self.max_visible = max_visible
        self.ttl_ms = ttl_ms
        self._seen: set[str] = set()
        self._visible: list[HudCard] = []

    @property
    def visible(self) -> list[HudCard]:
        return list(self._visible)

    @property
    def seen(self) -> frozenset[str]:
        return frozenset(self._seen)

    def consider(
        self,
        candidate: TermCandidate,
        blurb: str,
        shown_at_ms: int,
    ) -> HudCard | None:
        if candidate.confidence < self.min_confidence:
            return None
        if candidate.normalized in self._seen:
            return None

        card = HudCard(
            term=candidate.term,
            kind=candidate.kind,
            blurb=blurb,
            confidence=candidate.confidence,
            shown_at_ms=shown_at_ms,
            ttl_ms=self.ttl_ms,
        )

        self._seen.add(candidate.normalized)
        self._visible.append(card)
        self._visible.sort(key=lambda c: c.confidence, reverse=True)
        if len(self._visible) > self.max_visible:
            # Drop lowest confidence among currently visible.
            self._visible = self._visible[: self.max_visible]
            # If the new card was dropped, do not report it as shown.
            if card not in self._visible:
                return None
        return card

    def reset(self) -> None:
        self._seen.clear()
        self._visible.clear()
