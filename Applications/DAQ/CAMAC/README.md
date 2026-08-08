# CAMAC

CAMAC DAQ for Hoshin CAMAC controller

### Requirement
- **camdrv2 CAMAC Device Driver**: [https://github.com/SanshiroEnomoto/camdrv2](https://github.com/SanshiroEnomoto/camdrv2)

### Usage
#### Using pre-built App
- Up to four "standard" modules (`F0` to read, `F9` to clear, `F22` to enable LAM), up to 8 channels each
- Trigger by LAM from one of the four modules
- Readout using the standard `F0` function on LAM
- The data is stored in HDF5 files, one file per run.

```bash
cd PATH/TO/SLOWDASH/Applications/DAQ/CAMAC
slowdash --port=18881
```

#### Making your App
Use the `SlowPy CAMAC` module:

```python
from slowpy.control import control_system as ctrl
ctrl.import_control_module('CAMAC')

camac = ctrl.camac(crate=1)
module = camac.module(station=3)

while True:
    module.wait()
    
    for address in range(0, 8):
        data = module.channel(address).get()
        
    module.clear()
```

The `clear()` method uses the CAMAC standard clear function, `F9`.
If other function is necessary, do like
```python
module.command(function=10).get()
```

Similarly,`wait()` uses LAM and it calls `F26` at the start to enable LAM.
If other operations are necessary, do it manually using `command()`.


### Known Bugs
- Currently, only works with the Hoshin CCP-USB(V2) controller, with the `camdrv2` device driver.
- On the pre-built App, the CAMAC settings are not loaded properly after not operating the system (start/stop) for a long time (the data display time range, default 1 hour). If this happens, set the display time range very long and update the page by the "Reload Now" pull down menu, or restart the slowdash process.
