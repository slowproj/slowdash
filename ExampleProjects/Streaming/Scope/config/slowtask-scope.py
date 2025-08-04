import time
import numpy as np

from slowpy.control import control_system as ctrl
ctrl = ControlSystem()
fx = ctrl.value(3.2)
fy = ctrl.value(2.0)

from slowpy import Graph
from slowpy.store import DataStore_Redis
datastore = DataStore_Redis('redis://localhost/1')
next_store_time = 0


async def _initialize():
    ctrl.export(fx, name='fx.current')
    ctrl.export(fy, name='fy.current')
    
    
t0 = 0
async def _loop():
    global t0

    t0 += 0.05
    t = np.linspace(0, 1, 100)
    x1 = np.random.normal(np.cos((t+t0)*float(fx)*6.28), 0.0003)
    x2 = np.random.normal(np.sin((t+t0)*float(fy)*6.28), 0.0003)
    
    g_x, g_y, g_xy = Graph(), Graph(), Graph()
    g_x.add_point(t, x1)
    g_y.add_point(t, x2)
    g_xy.add_point(x1, x2)

    await ctrl.aio_publish(g_x, 'x.current')
    await ctrl.aio_publish(g_y, 'y.current')
    await ctrl.aio_publish(g_xy, 'xy.current')

    global next_store_time
    now = time.time()
    if now > next_store_time:
        datastore.update(g_x, tag='x')
        datastore.update(g_y, tag='y')
        datastore.update(g_xy, tag='xy')
        next_store_time = now + 5
        
    ctrl.sleep(0.5)
