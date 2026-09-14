# duh

Meeting HUD core: stream transcript events, detect terms, enrich with short blurbs, and show cards.

Fixture-first — no audio capture or live STT yet. Replay JSON fixtures or plain-text call dumps through the pipeline. Production will be audio → streaming STT → the same `TranscriptEvent` shape (no speaker names required).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Replay a fixture

**Mock backend** (closed lexicon in `fixtures/enrichments.json` — used by pytest goldens):

```bash
duh-replay fixtures/calls/finance-jargon-basic.json --backend mock --speed 0
```

**Groq backend** (open-world; no need to predefine every term):

```bash
# Edit .env in the repo root:
#   GROQ_API_KEY=your_key_here
#   GROQ_MODEL=openai/gpt-oss-120b
duh-replay fixtures/calls/acronym-and-jargon.json --backend groq --speed 0
```

**Plain-text call dump** (simulates STT: growing partials every N words, then one final per sentence):

```bash
duh-replay fixtures/calls/raw/kinn-intro.txt --backend groq --words 8 --speed 4
```

`.json` → timed fixture events. `.txt` / `.md` → sentence-split stream. Drop your own transcripts anywhere and point `duh-replay` at them.

`duh-replay` loads `.env` from the current directory automatically. If `GROQ_API_KEY` is set, `--backend` defaults to `groq`; otherwise `mock`.

`--speed 0` runs as fast as possible. `--speed 1` is realtime relative to event timestamps; `4` is 4×.

Term blurbs from Groq are cached under `.duh/cache/enrichments.json` (gitignored).

## Tests

```bash
pytest
```

Golden fixtures under `fixtures/calls/` run on the **mock** backend and stay deterministic. Groq paths are covered with a fake client (no network in CI).

## Layout

- `src/duh/` — models, detector, enricher, LLM analyzer, ranker, pipeline
- `src/duh/adapters/` — fixture replay, plain-text stream, terminal + in-memory HUD sinks
- `fixtures/enrichments.json` — canned blurbs for `MockEnricher`
- `fixtures/calls/` — timed transcript goldens
- `fixtures/calls/raw/` — plain-text call dumps for streaming replay
