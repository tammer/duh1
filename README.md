# duh

Meeting HUD core: stream transcript events, detect terms, enrich with short blurbs, and show cards.

Fixture-first by default. Replay JSON fixtures or plain-text call dumps through the pipeline, or capture what the Mac is playing and transcribe it live. Production will be audio → streaming STT → the same `TranscriptEvent` shape (no speaker names required).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

For live loopback capture (YouTube, Zoom output, etc.):

```bash
pip install -e ".[dev,live]"
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
#   GROQ_STT_MODEL=whisper-large-v3-turbo
#   DUH_CAPTURE_DEVICE=BlackHole 2ch
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

## Live loopback (system audio, not the mic)

`duh-live` captures **what the Mac is playing** (YouTube, Zoom output, etc.), transcribes chunks with Groq Whisper, and feeds the same HUD pipeline. It never defaults to the microphone and refuses device names that look like one.

macOS will not let Python read the default output device. Install [BlackHole](https://github.com/ExistentialAudio/BlackHole), then in Audio MIDI Setup create a Multi-Output Device that includes **BlackHole** and your speakers so you can hear audio while capturing it.

```bash
duh-live --list-devices
duh-live --device "BlackHole 2ch"
```

Or set `DUH_CAPTURE_DEVICE` in `.env`. Optional `--save-transcript out.txt` writes final lines for later `duh-replay`.

**YouTube recipe:** play a jargon-heavy talk (skip ads), run `duh-live`, and watch the terminal HUD. Cards lag the video by about 1–3 seconds. Do not commit recordings; saved transcripts are text only.

## Tests

```bash
pytest
```

Golden fixtures under `fixtures/calls/` run on the **mock** backend and stay deterministic. Groq paths are covered with a fake client (no network in CI).

## Layout

- `src/duh/` — models, detector, enricher, LLM analyzer, ranker, pipeline, live CLI
- `src/duh/adapters/` — fixture replay, plain-text stream, loopback capture, terminal + in-memory HUD sinks
- `fixtures/enrichments.json` — canned blurbs for `MockEnricher`
- `fixtures/calls/` — timed transcript goldens
- `fixtures/calls/raw/` — plain-text call dumps for streaming replay
