
from slowpy.control import control_system as ctrl
ctrl.import_control_module('DummyDevice')
device = ctrl.randomwalk_device()

import slowpy
hist = slowpy.Histogram(100, 0, 20)
hist.add_stat(slowpy.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))


from slowpy.mesh import Tasklet
tasklet = Tasklet()

@tasklet.loop(interval=0.2, ticks=5)
async def loop(ticks):
    for ch in range(4):
        x = float(device.ch(ch))+10
        await ctrl.aio_stream(f'ch{ch:02d}', x)

        hist.fill(x)
        
    if ticks:
        await ctrl.aio_stream('hist', hist)
