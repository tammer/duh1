from __future__ import annotations

import json
from pathlib import Path

from duh.models import TermKind


def default_cache_path() -> Path:
    return Path.cwd() / ".duh" / "cache" / "enrichments.json"


class TermCache:
    """Persistent term → {kind, blurb} cache on disk."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_cache_path()
        self._entries: dict[str, dict[str, str]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            self._entries = {}
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._entries = {}
            return
        if isinstance(raw, dict):
            self._entries = {str(k).lower(): v for k, v in raw.items() if isinstance(v, dict)}
        else:
            self._entries = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._entries, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def known_terms(self) -> list[str]:
        return sorted(self._entries.keys())

    def get(self, term: str) -> dict[str, str] | None:
        return self._entries.get(term.lower())

    def put(self, term: str, *, kind: TermKind | str, blurb: str) -> None:
        self._entries[term.lower()] = {"kind": str(kind), "blurb": blurb}
        self._save()

    def put_many(self, items: list[tuple[str, TermKind | str, str]]) -> None:
        if not items:
            return
        for term, kind, blurb in items:
            self._entries[term.lower()] = {"kind": str(kind), "blurb": blurb}
        self._save()
