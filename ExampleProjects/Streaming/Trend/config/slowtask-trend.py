
import time, random, logging
import slowpy as slp

from slowpy.control import control_system as ctrl
ctrl.import_control_module("DummyDevice")
device = ctrl.randomwalk_device(decay=0.01)
print("Dummy data generator loaded")

from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///SlowTestData', 'ts_data')

from slowpy import Trend
trend = Trend(length=60, tick=0.1)


async def _loop():
    t = time.time()

    x = [ float(device.ch(0).get()) + 10*random.random() for i in range(5) ]
    for xk in x:
        trend.fill(t, xk)
        
    await ctrl.aio_publish(trend, name="trend")
    await ctrl.aio_publish(trend.timeseries(), name="trend_ts")
    
    datastore.append(x[-1], tag='x')
    await ctrl.aio_publish(x[-1], name="value")
        
    await ctrl.aio_sleep(0.2)
