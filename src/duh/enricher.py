from __future__ import annotations

import json
from pathlib import Path

from duh.detector import default_enrichments_path
from duh.models import TermKind
from duh.ports import Enricher


class MockEnricher:
    """Lookup blurbs from a canned enrichments JSON map."""

    def __init__(self, path: Path | None = None) -> None:
        path = path or default_enrichments_path()
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._entries: dict[str, dict[str, str]] = {
            key.lower(): value for key, value in raw.items()
        }

    def enrich(self, term: str, kind: TermKind) -> str | None:
        entry = self._entries.get(term.lower())
        if entry is None:
            return None
        return entry.get("blurb")

    def kind_for(self, term: str) -> TermKind | None:
        entry = self._entries.get(term.lower())
        if entry is None:
            return None
        return entry.get("kind")  # type: ignore[return-value]


class CachingEnricher:
    """In-process cache around any Enricher."""

    def __init__(self, inner: Enricher) -> None:
        self._inner = inner
        self._cache: dict[str, str | None] = {}

    def enrich(self, term: str, kind: TermKind) -> str | None:
        key = term.lower()
        if key not in self._cache:
            self._cache[key] = self._inner.enrich(term, kind)
        return self._cache[key]
