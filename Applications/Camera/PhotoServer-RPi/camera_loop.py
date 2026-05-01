#!/usr/bin/env python3

import subprocess
import time
from datetime import datetime
from pathlib import Path

OUT = "photo.jpg"
INTERVAL_MS = "1000"
RESTART_DELAY = 2
LOG = Path("camera_loop.log")

CMD = [
    "rpicam-still",
    "-n",
    "-t", "0",
    "--timelapse", INTERVAL_MS,
    "-o", OUT,
]


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG.open("a") as f:
        f.write(f"{timestamp} {message}\n")


while True:
    log("starting camera command")

    with LOG.open("a") as f:
        proc = subprocess.run(
            CMD,
            stdout=f,
            stderr=subprocess.STDOUT,
        )

    log(f"camera command exited with code {proc.returncode}")
    log(f"restarting in {RESTART_DELAY}s")

    time.sleep(RESTART_DELAY)

