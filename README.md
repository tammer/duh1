# duh

Meeting HUD core: stream transcript events, detect terms, enrich with short blurbs, and show cards.

This first cut is **fixture-first** — no audio capture or live STT. Replay JSON call fixtures through the pipeline to iterate on detection and ranking.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Replay a fixture

```bash
duh-replay fixtures/calls/finance-jargon-basic.json --speed 0
duh-replay fixtures/calls/finance-jargon-basic.json --speed 4
```

`--speed 0` runs as fast as possible. `--speed 1` is realtime relative to fixture timestamps; `4` is 4×.

## Tests

```bash
pytest
```

Golden fixtures under `fixtures/calls/` assert which terms must appear and which must not.

## Layout

- `src/duh/` — models, detector, enricher, ranker, pipeline
- `src/duh/adapters/` — fixture replay, terminal + in-memory HUD sinks
- `fixtures/enrichments.json` — canned term blurbs for `MockEnricher`
- `fixtures/calls/` — timed transcript goldens
