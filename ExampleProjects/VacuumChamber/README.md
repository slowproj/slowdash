# Webcam OCR — Vacuum Test Chamber Pressure Monitoring

Reads the chamber pressure from a **KJLC® 354 Series Ion Gauge** (Kurt J. Lesker) using Claude vision OCR. A webcam or IP camera is pointed at the front-panel display; the slowtask captures frames every 30 seconds, sends them to Claude, and stores the extracted pressure value in a local SQLite database.

## Hardware

- **Gauge**: KJLC® 354 Series Ion Gauge with Integrated Controller & Display
- **Camera**: any IP camera or Raspberry Pi camera accessible via HTTP JPEG endpoint

## Quick Start

1. **Configure the camera URL** — edit `config/slowagent-IonGauge.json` and set `capture.source` to the JPEG endpoint of your camera (e.g., `http://192.168.1.50/snapshot.jpg`).

2. **Run slowdash** from this directory:
   ```
   slowdash --port=18882
   ```
   Use a different port than any other running slowdash instance.

3. Open `http://localhost:18882` in a browser.

## Dashboard Features

- **Recent Frames** — carousel of the last captured batch (cycles automatically)
- **Editable Extraction Prompt** — edit the LLM prompt inline, click **Save Prompt**, the slowtask reloads within ~10 s
- **Force Refresh** — button to bypass dedup and immediately re-run the LLM
- **Live Plot** — rolling 24-hour pressure trend

## Configuration

Edit `config/slowagent-IonGauge.json` to change:

| Field | Description |
|---|---|
| `capture.source` | HTTP URL to the camera JPEG endpoint |
| `capture.cycle_seconds` | How often to capture & extract (default 30 s) |
| `capture.frames_per_cycle` | Number of frames per batch (default 5) |
| `llm.model` | Claude model to use |
| `llm.prompt` | Extraction instructions sent to Claude |
| `channels[0].ymin` / `ymax` | Valid pressure range in Torr for validation & plot axis |

The slowtask hot-reloads the JSON within ~10 seconds of any save; no restart needed.

## Data

- **Database**: `VacuumChamber.db` (SQLite, append-only — survives restarts)
- **Schema**: `data[channel]@timestamp(unix)=value`, channel name is `pressure`
- To wipe history: `rm VacuumChamber.db`

## Notes

- The display must be clearly visible in the captured frames; ensure adequate lighting.
- The KJLC 354 shows pressure in scientific notation (e.g., `1.23 E-7`). The LLM converts this to a float before storing.
- Uses Claude Code (OAuth) — no API key needed. The subprocess runs with `--tools Read` only and cannot access files outside the frame batch directory.
- `last_images/` holds only the most recent capture batch (wiped before each new cycle).
