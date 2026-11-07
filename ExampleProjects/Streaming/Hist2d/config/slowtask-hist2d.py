
import slowpy
from slowpy.mesh import Tasklet
tasklet = Tasklet()
hist2d = slowpy.Histogram2d(100, 0, 100, 32, 0, 100)

from slowpy.control import control_system as ctrl
import numpy as np

@tasklet.loop(interval=1.0)
async def loop():
    hist2d.clear()
    for i in range(10000):
        x = np.random.normal(50, 20)
        y = np.random.normal(50, 20)
        hist2d.fill(x, y)
        
    await ctrl.aio_stream("hist2d", hist2d)
