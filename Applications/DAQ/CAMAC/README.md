# CAMAC

CAMAC DAQ for Hoshin CAMAC controller

### Requirement
- **camdrv2 CAMAC Device Driver**: [https://github.com/SanshiroEnomoto/camdrv2](https://github.com/SanshiroEnomoto/camdrv2)

### Usage
#### Using pre-built App
```bash
cd PATH/TO/SLOWDASH/Applications/DAQ/CAMAC
slowdash --port=18881
```

#### Making your App
Use SlowPy CAMAC module:

```python
camac = CamacNode(crate=1)
module = camac.module(station=3)

while True:
    module.wait()
    
    for address in range(0, 2):
        data = module.channel(address).get()
        
    module.clear()
```

The `clear()` method uses the CAMAC standard clear function, `F9`.
If other function is necessary, do like
```python
    module.command(function=10).get()
```

Similarly,`wait()` uses LAM and it calls `F26` at the start to enable LAM.
If other procedure is necessary, do it manually.


### Known Bugs
- Currently, only works with the Hoshin CCP-USB(V2) controller, with the `camdrv2` device driver.
- On the pre-built App, the CAMAC settings are not loaded properly after not operating the system (start/stop) for a long time (the data display time, default 1 hour). If this happens, set the display time range very long and update the page by "Reload Now" pull down, or restart the slowdash process.
