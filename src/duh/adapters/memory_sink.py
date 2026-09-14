from __future__ import annotations

from duh.models import HudCard


class InMemoryHudSink:
    """Collect shown cards for tests and headless replay."""

    def __init__(self) -> None:
        self.cards: list[HudCard] = []

    def show(self, card: HudCard) -> None:
        self.cards.append(card)

    def clear(self) -> None:
        self.cards.clear()

    @property
    def terms(self) -> list[str]:
        return [c.term for c in self.cards]

    @property
    def normalized_terms(self) -> list[str]:
        return [c.term.lower() for c in self.cards]
