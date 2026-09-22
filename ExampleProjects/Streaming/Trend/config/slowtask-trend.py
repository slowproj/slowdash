
import time

from slowpy.control import control_system as ctrl
ctrl.import_control_module("DummyDevice")
device = ctrl.randomwalk_device(decay=0.1, walk=10)
print("Dummy data generator loaded")

from slowpy import Trend
trend = Trend(length=60, tick=1)

from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///SlowTestData', 'ts_data')

from slowpy.mesh import Tasklet
tasklet = Tasklet()


@tasklet.loop(interval=0.2, ticks=5)
async def loop(ticks):
    t = time.time()
    x = float(device.ch(0).get())
    trend.fill(t, x)

    if ticks:
        await ctrl.aio_stream("trend", trend)
        await ctrl.aio_stream("trend_ts", trend.timeseries())
        await ctrl.aio_stream("value", x)
        datastore.append(x, tag='x')
