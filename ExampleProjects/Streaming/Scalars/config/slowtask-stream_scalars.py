
from slowpy.control import control_system as ctrl
ctrl.import_control_module('DummyDevice')
device = ctrl.randomwalk_device()

import slowpy as slp
h = slp.Histogram(100, 0, 20)
h.add_stat(slp.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))


async def _loop():
    for ch in range(4):
        x = float(device.ch(ch))+10
        await ctrl.aio_stream(f'ch{ch:02d}', x)

        h.fill(x)
        await ctrl.aio_stream('hist', h)
        
    await ctrl.aio_sleep(0.2)
