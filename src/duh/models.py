from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


TermKind = Literal["company", "acronym", "jargon", "other"]
EventSource = Literal["fixture", "live"]


class TranscriptEvent(BaseModel):
    id: str
    text: str
    is_final: bool = True
    t_ms: int = 0
    end_ms: int | None = None
    speaker: str | None = None
    source: EventSource = "fixture"


class TermCandidate(BaseModel):
    term: str
    normalized: str
    kind: TermKind
    confidence: float = Field(ge=0.0, le=1.0)
    event_id: str
    t_ms: int


class HudCard(BaseModel):
    term: str
    kind: TermKind
    blurb: str
    confidence: float = Field(ge=0.0, le=1.0)
    shown_at_ms: int
    ttl_ms: int = 15_000


class FixtureExpect(BaseModel):
    terms: list[str] = Field(default_factory=list)
    must_not_show: list[str] = Field(default_factory=list)


class CallFixture(BaseModel):
    name: str
    events: list[TranscriptEvent]
    expect: FixtureExpect | None = None
