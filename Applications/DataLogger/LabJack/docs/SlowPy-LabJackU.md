# SlowPy Control Plugin for LabJack U3 / U6 / U12

This module provides a SlowPy/Control interface for LabJack U3, U6, and U12 devices.

It wraps LabJackPython and provides a mostly common interface for:

* Analog Input (AIN)
* Analog Output (AOUT / DAC)
* Digital Input (DIN)
* Digital Output (DOUT)

Additional U6 features include:

* Internal temperature measurement
* LED control
* Analog-input resolution selection
* Programmable gain
* Differential analog input

## Setup Procedure

### Low-Level USB Driver Installation

LabJack documentation:
[https://support.labjack.com/docs/exodriver-downloads-for-ud-series-linux-and-macos-](https://support.labjack.com/docs/exodriver-downloads-for-ud-series-linux-and-macos-)

First install the USB development package:

```bash
sudo apt install libusb-1.0-0-dev
```

Then download and install the LabJack Exodriver package, for example:
Download link (Apr 2026): [https://github.com/labjack/exodriver/archive/refs/heads/master.zip](https://github.com/labjack/exodriver/archive/refs/heads/master.zip)

```bash
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


## Usage

### Creating an Instance
#### U3

```python
from control_LabJackU import LabJackU3

labjack = LabJackU3()
```

By default,

```python
fio_config = 0x0f
```

is used, which configures FIO0-FIO3 as analog channels and FIO4-FIO7 as digital channels.

A different configuration can be specified explicitly:

```python
labjack = LabJackU3(fio_config=0x03)
```

#### U6

```python
from control_LabJackU import LabJackU6

labjack = LabJackU6()
```

#### U12

```python
from control_LabJackU import LabJackU12

labjack = LabJackU12()
```

### Common Interface

U3, U6, and U12 provide a common high-level interface:

```python
labjack.ain(ch).get()
labjack.aout(ch).set(value)

labjack.din(ch).get()
labjack.dout(ch).set(value)
```

This hides much of the device-specific API difference in LabJackPython.

### Analog Input

#### U3

Read an analog input with:

```python
value = labjack.ain(0).get()
print(value)
```

The U3 implementation uses `getAIN()`.

With the default FIO configuration:

```text
AIN0 = FIO0
AIN1 = FIO1
AIN2 = FIO2
AIN3 = FIO3
```

#### U6

Basic analog input:

```python
value = labjack.ain(0).get()
```

The resolution, gain, and differential mode can also be specified:

```python
value = labjack.ain(
    0,
    resolution=0,
    gain=0,
    differential=False,
).get()
```

Arguments:

```text
ch:
    0 ... 13

resolution:
    0       default
    1 ... 8 resolution index

gain:
    0   x1
    1   x10
    2   x100
    3   x1000
    15  auto range

differential:
    False   single-ended
    True    differential
```

These values are passed to LabJackPython as `resolutionIndex`, `gainIndex`, and `differential`.

##### Differential Input Example

Read AIN0 relative to AIN1:

```python
value = labjack.ain(
    0,
    gain=0,
    differential=True,
).get()
```

Read AIN2 relative to AIN3:

```python
value = labjack.ain(
    2,
    gain=0,
    differential=True,
).get()
```

#### U12

Single-ended analog input:

```python
value = labjack.ain(0).get()
```

Differential analog input:

```python
value = labjack.ain(8, gain=7).get()
```

Channel numbering:

```text
ch = 0 ... 7
    single-ended

ch = 8 ... 11
    differential
```

For differential input, a gain can be specified:

```text
gain = 0 ... 7

0  x1
1  x2
2  x4
3  x5
4  x8
5  x10
6  x16
7  x20
```

Internally, the plugin uses LabJackPython's `eAnalogIn()`.

### Analog Output

Analog output is set using:

```python
labjack.aout(ch).set(voltage)
```

For example, to set DAC0 to 3.21 V:

```python
labjack.aout(0).set(3.21)
```

#### U3

```python
labjack.aout(0).set(2.5)
labjack.aout(1).set(1.0)
```

The U3 implementation uses `voltageToDACBits()` together with `DAC0_8` and `DAC1_8`.

#### U6

```python
labjack.aout(0).set(2.5)
labjack.aout(1).set(1.0)
```

The U6 implementation uses the 16-bit DAC feedback commands.

#### U12

```python
labjack.aout(0).set(2.5)
labjack.aout(1).set(1.0)
```

Since U12 `eAnalogOut()` sets both DAC0 and DAC1 at the same time, the plugin stores the current values internally.

### Digital Input

#### U3

```python
state = labjack.din(4).get()
```

With the default U3 configuration, FIO4-FIO7 are used as digital I/O.

```python
for ch in range(4, 8):
    print(ch, labjack.din(ch).get())
```

The implementation uses `getDIState()`.

#### U6

```python
state = labjack.din(0).get()
```

Channel numbering:

```text
0 ... 7     FIO0 ... FIO7
8 ... 15    EIO0 ... EIO7
16 ... 19   CIO0 ... CIO3
```

#### U12

```python
state = labjack.din(0).get()
```

For DB25 digital input:

```python
state = labjack.dbin(0).get()
```

The implementation uses `eDigitalIn()`.

### Digital Output

Digital outputs are controlled with:

```python
labjack.dout(ch).set(True)
labjack.dout(ch).set(False)
```

Integer values can also be used:

```python
labjack.dout(ch).set(1)
labjack.dout(ch).set(0)
```

#### U3

```python
labjack.dout(4).set(True)
labjack.dout(4).set(False)
```

The U3 implementation uses `setDOState()`.

#### U6

```python
labjack.dout(0).set(True)
```

The U6 implementation also uses `setDOState()`.

#### U12

```python
labjack.dout(0).set(True)
```

For DB25 digital output:

```python
labjack.dbout(0).set(True)
```

## Internal Temperature (U6 only)

The U6 internal temperature can be read with:

```python
temperature = labjack.temperature().get()
print(temperature)
```

The implementation reads the internal temperature channel and applies the LabJack calibration function.


### LED Control (U6 only)

The U6 LED can be controlled with:

```python
led = labjack.led()

led.set(True)
led.set(False)
```

Example:

```python
import time

led = labjack.led()

for i in range(10):
    led.set(not led.get())
    time.sleep(0.2)
```

### Configuration Information

These return the results of LabJackPython's `configU3()` and `configU6()` calls.

#### U3:

```python
print(labjack.config().get())
```

#### U6:

```python
print(labjack.config().get())
```


### Complete Examples

#### U3

```python
from control_LabJackU import LabJackU3

labjack = LabJackU3()

print("Config:", labjack.config().get())

# Digital output
labjack.dout(4).set(False)

# Digital input
for ch in range(4, 8):
    print(f"DIN{ch}: {labjack.din(ch).get()}")

# Analog output
labjack.aout(0).set(3.21)

# Analog input
for ch in range(4):
    print(f"AIN{ch}: {labjack.ain(ch).get()}")

labjack.close()
```

#### U6

```python
from control_LabJackU import LabJackU6

labjack = LabJackU6()

print("Config:", labjack.config().get())

# Digital output
labjack.dout(0).set(False)

# Digital input
for ch in range(1, 8):
    print(f"DIN{ch}: {labjack.din(ch).get()}")

# Analog output
labjack.aout(0).set(3.21)

# Single-ended analog inputs
for ch in range(8):
    print(
        f"AIN{ch}: "
        f"{labjack.ain(ch, resolution=0, gain=0).get()}"
    )

# Differential analog inputs
for ch in range(4):
    pos = 2 * ch
    neg = pos + 1

    value = labjack.ain(
        pos,
        resolution=0,
        gain=0,
        differential=True,
    ).get()

    print(f"AIN{pos}-AIN{neg}: {value}")

# Internal temperature
print("Temperature:", labjack.temperature().get())

labjack.close()
```

#### U12

```python
from control_LabJackU import LabJackU12

labjack = LabJackU12()

# Single-ended analog inputs
for ch in range(8):
    print(f"AIN{ch}: {labjack.ain(ch).get()}")

# Differential analog inputs
for ch in range(8, 12):
    print(
        f"AIN{ch}: "
        f"{labjack.ain(ch, gain=7).get()}"
    )

labjack.close()
```

## Supported Interface Summary

| Function              | U3  | U6  | U12 |
| --------------------- | --- | --- | --- |
| `ain(ch).get()`       | Yes | Yes | Yes |
| `aout(ch).set(v)`     | Yes | Yes | Yes |
| `din(ch).get()`       | Yes | Yes | Yes |
| `dout(ch).set(v)`     | Yes | Yes | Yes |
| `config().get()`      | Yes | Yes | -   |
| `temperature().get()` | -   | Yes | -   |
| `led().set(v)`        | -   | Yes | -   |
| `dbout(ch).set(v)`    | -   | -   | Yes |

