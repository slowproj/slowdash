# WebcamOCR — LLM-based monitoring for screen-only instruments

Demo project for the [slowdash-agent-tools](../../slowdash-agent-tools)
submodule. A Claude vision model reads the front display of an Omega CN1500
multi-zone temperature controller from webcam frames and writes each zone's
value to the SlowDash datastore as a normal time-series channel.

## What's in here

```
WebcamOCR/
├── SlowdashProject.yaml          # data_source + slowtask + sd_agent.py user module
├── config/
│   ├── slowtask-webcam_ocr.py    # symlink → slowdash-agent-tools/slowtask/...
│   ├── slowagent-Omega.json      # capture rate, prompt, channel list (edit me!)
│   └── slowplot-Omega.json       # right-hand panel: per-zone time-series
└── last_images/
    ├── IMG_1574.JPG              # sample frame ("21 C", CTR1 lit)
    └── Screenshot…png            # sample frame ("40 C")
```

The default `capture.source` in `slowagent-Omega.json` is `file://./last_images`,
which makes the demo run *without a real webcam* — it just cycles through the
two sample images. Drop in more JPEGs/PNGs and they'll be picked up on the
next scan. Replace with `http://your-pi.local/photo.cgi` (or any HTTP URL
that returns a fresh JPEG on each GET) to point at a real camera.

## Run

```bash
# 1.  Save your Anthropic API key once (see slowdash-agent-tools/README.md)
mkdir -p ~/.config/slowdash
printf 'anthropic_api_key = "sk-ant-..."\n' > ~/.config/slowdash/secrets.toml
chmod 600 ~/.config/slowdash/secrets.toml

# 2.  Start slowdash from this directory
cd ExampleProjects/WebcamOCR
slowdash --port=18881

# 3.  Open in a browser
#     http://localhost:18881/                              ← home page
#     http://localhost:18881/slowagent.html?config=slowagent-Omega.json
```

The home page shows the layout under "SlowAgent" alongside any slowdash
or slowplot pages. Clicking it opens the agent page directly with the
right `?config=` parameter.

## Editing on the fly

- Change the prompt in the textbox on the agent page and click **Save Prompt**
  — the slowtask polls the layout file mtime and reloads within a couple of
  seconds without restarting.
- Edit `slowagent-Omega.json` directly to add or remove channels, change the
  capture rate, or point at a different camera.
- Edit `slowplot-Omega.json` to change colours, axis ranges, or panel layout
  on the right-hand side.

## Security notes

- The Anthropic API key never leaves `~/.config/slowdash/secrets.toml`. It
  is not stored in this repo or in the SQLite datastore.
- Captured frames are kept only in process memory and the `LatestImage`
  blob channel. They are deleted from the in-memory buffer immediately
  after the LLM call returns.
- The LLM is asked for JSON values, never for code. The
  `slowagent.sandbox` module is scaffolded but not used by this slowtask.
