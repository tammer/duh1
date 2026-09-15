# Duh (macOS overlay)

Floating HUD that starts the Python `duh-worker`, captures BlackHole loopback audio, and shows jargon cards over your meetings.

## Prerequisites

1. Repo setup (from the repository root):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,live]"
```

2. `.env` in the repo root with at least `GROQ_API_KEY=…`.

3. [BlackHole 2ch](https://github.com/ExistentialAudio/BlackHole) installed.

4. **Multi-Output Device** (so you can hear *and* capture):
   - Open **Audio MIDI Setup**
   - **+** → **Create Multi-Output Device**
   - Check **BlackHole 2ch** and your speakers/headphones
   - In **System Settings → Sound → Output**, select that Multi-Output Device

5. Xcode 15+ (macOS 14+ deployment target).

## Run

```bash
open apps/macos/Duh.xcodeproj
```

Select the **Duh** scheme and press Run. A floating panel appears (menu-bar-less accessory app).

- **Capture device** defaults to `BlackHole 2ch`
- **Worker path** defaults to `<repo>/.venv/bin/duh-worker` (override if needed)
- Click **Start** — grant microphone/audio permission if macOS prompts (needed for PortAudio loopback)
- Play Zoom / Teams / Meet / YouTube through the Multi-Output Device

## Manual worker check

```bash
duh-worker --device "BlackHole 2ch"
```

You should see JSONL on stdout (`status`, `transcript`, `card`). Diagnostics go to stderr.

## Notes

- This MVP does **not** bundle Python inside the `.app`; it shells out to your venv.
- `duh-live` remains the terminal HUD; `duh-worker` is the machine-readable twin for this overlay.
