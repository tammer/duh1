from __future__ import annotations

import json
import re
from pathlib import Path

from duh.models import TermCandidate, TermKind, TranscriptEvent

# Common ALL-CAPS tokens that are not useful acronyms in meeting speech.
ACRONYM_DENYLIST = frozenset(
    {
        "OK",
        "OKAY",
        "FYI",
        "ASAP",
        "CEO",
        "CFO",
        "CTO",
        "USA",
        "US",
        "UK",
        "AM",
        "PM",
        "ID",
        "AI",
        "IT",
        "HR",
        "PDF",
        "FAQ",
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "FY",
    }
)

_ACRONYM_RE = re.compile(r"\b([A-Z]{2,6})\b")
_TITLE_WORD_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b")


def default_enrichments_path() -> Path:
    """Resolve enrichments.json shipped with the package or at repo root."""
    pkg = Path(__file__).resolve().parent / "fixtures" / "enrichments.json"
    if pkg.is_file():
        return pkg
    repo = Path(__file__).resolve().parents[2] / "fixtures" / "enrichments.json"
    return repo


def load_lexicon(path: Path | None = None) -> dict[str, TermKind]:
    path = path or default_enrichments_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {key.lower(): entry["kind"] for key, entry in data.items()}


class TermDetector:
    """Heuristic term detector: acronyms, lexicon hits, title-case names."""

    def __init__(self, lexicon: dict[str, TermKind] | None = None) -> None:
        self._lexicon = lexicon if lexicon is not None else load_lexicon()

    def detect(self, event: TranscriptEvent) -> list[TermCandidate]:
        if not event.is_final:
            return []

        found: dict[str, TermCandidate] = {}

        for match in _ACRONYM_RE.finditer(event.text):
            raw = match.group(1)
            if raw in ACRONYM_DENYLIST:
                continue
            # Skip FY27-style tokens already partially matched; require pure acronym.
            if any(ch.isdigit() for ch in raw):
                continue
            kind = self._lexicon.get(raw.lower(), "acronym")
            conf = 0.9 if raw.lower() in self._lexicon else 0.7
            self._add(found, raw, kind, conf, event)

        for match in _TITLE_WORD_RE.finditer(event.text):
            raw = match.group(1)
            # Skip sentence starters that aren't in the lexicon unless multi-word.
            words = raw.split()
            if len(words) == 1 and raw.lower() not in self._lexicon:
                # Single Title-Case word: only keep if lexicon knows it.
                continue
            if len(words) >= 2 or raw.lower() in self._lexicon:
                kind = self._lexicon.get(raw.lower(), "company")
                conf = 0.95 if raw.lower() in self._lexicon else 0.65
                self._add(found, raw, kind, conf, event)

        # Lexicon word/phrase scan (case-insensitive) for jargon like "swaption".
        for key, kind in self._lexicon.items():
            if key in found:
                continue
            # Word-boundary-ish match for multi-word and single tokens.
            pattern = re.compile(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", re.I)
            m = pattern.search(event.text)
            if not m:
                continue
            display = m.group(0)
            # Prefer original casing from text.
            conf = 0.95
            self._add(found, display, kind, conf, event)

        return list(found.values())

    @staticmethod
    def _add(
        found: dict[str, TermCandidate],
        term: str,
        kind: TermKind,
        confidence: float,
        event: TranscriptEvent,
    ) -> None:
        normalized = term.lower()
        existing = found.get(normalized)
        if existing and existing.confidence >= confidence:
            return
        found[normalized] = TermCandidate(
            term=term,
            normalized=normalized,
            kind=kind,
            confidence=confidence,
            event_id=event.id,
            t_ms=event.t_ms,
        )
