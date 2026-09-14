from __future__ import annotations

import json
from typing import Any, cast

from pydantic import BaseModel, Field, ValidationError

from duh.cache import TermCache
from duh.groq_client import ChatClient
from duh.models import TermKind, TranscriptEvent

SYSTEM_PROMPT = """\
You are a meeting HUD assistant. Given one transcript utterance, return terms a \
professional listener may need defined right now.

Rules:
- Include companies, products, jargon, and non-obvious acronyms.
- Skip filler and common words (okay, slide, tomorrow, thanks, next, plan, etc.).
- Each blurb must be essentials only, at most 280 characters.
- If nothing is worth explaining, return an empty JSON array [].
- Output ONLY a JSON array of objects with keys:
  term (string), kind (company|acronym|jargon|other), blurb (string),
  confidence (number 0-1).
- Do NOT redefine terms listed in already_known; only return NEW terms from this utterance.
"""

_VALID_KINDS = frozenset({"company", "acronym", "jargon", "other"})


class AnalyzedTerm(BaseModel):
    term: str
    kind: TermKind = "other"
    blurb: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class GroqUtteranceAnalyzer:
    """One Groq call per final utterance → open-world terms + blurbs."""

    def __init__(
        self,
        client: ChatClient,
        cache: TermCache | None = None,
    ) -> None:
        self.client = client
        self.cache = cache or TermCache()
        # Session-scoped: avoid re-asking the model for terms already returned.
        self._session_known: set[str] = set()

    def analyze(self, event: TranscriptEvent) -> list[AnalyzedTerm]:
        if not event.is_final:
            return []
        text = event.text.strip()
        if not text:
            return []

        already_known = sorted(self._session_known)
        user_payload = {
            "utterance": text,
            "already_known": already_known,
        }
        raw = self.client.chat_json(SYSTEM_PROMPT, json.dumps(user_payload))
        terms = self._parse_terms(raw)

        resolved: list[AnalyzedTerm] = []
        to_store: list[tuple[str, TermKind, str]] = []
        for item in terms:
            normalized = item.term.lower()
            if normalized in self._session_known:
                continue

            cached = self.cache.get(item.term)
            if cached and cached.get("blurb"):
                kind = _coerce_kind(cached.get("kind"), item.kind)
                blurb = cached["blurb"]
            else:
                kind = item.kind
                blurb = item.blurb
                to_store.append((item.term, kind, blurb))

            resolved.append(
                AnalyzedTerm(
                    term=item.term,
                    kind=kind,
                    blurb=blurb,
                    confidence=item.confidence,
                )
            )
            self._session_known.add(normalized)

        self.cache.put_many(to_store)
        return resolved

    @staticmethod
    def _parse_terms(raw: Any) -> list[AnalyzedTerm]:
        if raw is None:
            return []
        if isinstance(raw, dict):
            raw = raw.get("terms", raw.get("items", []))
        if not isinstance(raw, list):
            return []
        out: list[AnalyzedTerm] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                out.append(AnalyzedTerm.model_validate(item))
            except ValidationError:
                continue
        return out


def _coerce_kind(value: str | None, fallback: TermKind) -> TermKind:
    if value in _VALID_KINDS:
        return cast(TermKind, value)
    return fallback
