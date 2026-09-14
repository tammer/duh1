from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from duh.models import HudCard, TranscriptEvent


class TerminalHudSink:
    """Rich terminal HUD: transcript lines + card panels."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._cards: list[HudCard] = []

    def show_transcript(self, event: TranscriptEvent) -> None:
        speaker = f"[cyan]{event.speaker}[/cyan]: " if event.speaker else ""
        final = "" if event.is_final else " [dim](partial)[/dim]"
        self.console.print(
            f"[dim]{event.t_ms:>6}ms[/dim]  {speaker}{event.text}{final}"
        )

    def show(self, card: HudCard) -> None:
        self._cards.append(card)
        # Keep display list aligned with ranker max of 3 for readability.
        self._cards = self._cards[-3:]
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("term", style="bold yellow")
        table.add_column("blurb", style="white")
        for c in self._cards:
            table.add_row(f"{c.term} [{c.kind}]", c.blurb)
        self.console.print(Panel(table, title="HUD", border_style="green"))

    def clear(self) -> None:
        self._cards.clear()
