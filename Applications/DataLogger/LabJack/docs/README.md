# LabJack U-Series

## LabJack Library Installation

### Low-Level USB Driver Installation
LabJack documentation:
[https://support.labjack.com/docs/exodriver-downloads-for-ud-series-linux-and-macos-](https://support.labjack.com/docs/exodriver-downloads-for-ud-series-linux-and-macos-)

First install the USB development package:

```bash
sudo apt install libusb-1.0-0-dev
```

Then download and install the LabJack Exodriver package.
Download link (Apr 2026): [https://github.com/labjack/exodriver/archive/refs/heads/master.zip](https://github.com/labjack/exodriver/archive/refs/heads/master.zip)

```bash
unzip master.zip
cd exodriver-master
sudo ./install.sh
```

### Python Package
Install LabJackPython with:

```bash
slowdash-activate-venv
pip install LabJackPython
```


## Testing
```
slowdash-activate-venv
cd PATH/TO/SLOWDASH/lib/slowpy/slowpy/control
python control_LabJackU.py   # edit the file before running
```


## Testing
