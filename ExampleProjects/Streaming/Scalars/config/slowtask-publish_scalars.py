
import sys, os, asyncio, time, json, logging
from slowpy.control import control_system as ctrl

ctrl.import_control_module('DummyDevice')
device = ctrl.randomwalk_device()


import slowpy as slp
h = slp.Histogram(100, 0, 20)
h.add_stat(slp.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))


async def _loop():
    for ch in range(4):
        x = float(device.ch(ch))+10
        await ctrl.publish(x, name=f"ch{ch:02d}")

        h.fill(x)
        await ctrl.publish(h, name="hist")        
        
    await asyncio.sleep(0.2)
