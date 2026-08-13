# LabJack U-Series

## Setup Procedure
LabJack documentation:
[https://support.labjack.com/docs/exodriver-downloads-for-ud-series-linux-and-macos-](https://support.labjack.com/docs/exodriver-downloads-for-ud-series-linux-and-macos-)

### Python Package
Install LabJackPython with:

```bash
pip install LabJackPython
```

### Low-Level USB Driver Installation
First install the USB development package:

```bash
sudo apt install libusb-1.0-0-dev
```

Then download and install the LabJack Exodriver package.
Download link (Apr 2026)[https://github.com/labjack/exodriver/archive/refs/heads/master.zip](https://github.com/labjack/exodriver/archive/refs/heads/master.zip)

```bash
unzip master.zip
cd exodriver-master
sudo ./install.sh
```
