import time
import numpy as np

from slowpy.control import ControlSystem, ValueNode
ctrl = ControlSystem()

from slowpy import Graph
from slowpy.store import DataStore_Redis
datastore = DataStore_Redis('redis://localhost/1')
next_store_time = 0


fx = 3.2
fy = 2.0
x = ValueNode(Graph().to_json())
y = ValueNode(Graph().to_json())
xy = ValueNode(Graph().to_json())


def _export():
    return [ ('x', x), ('y', y), ('xy', xy) ]



t0 = 0
async def _loop():
    global t0
    t0 += 0.05
    t = np.linspace(0, 1, 100)
    x1 = np.random.normal(np.cos((t-t0)*fx*6.28), 0.0003)
    x2 = np.random.normal(np.sin((t-t0)*fy*6.28), 0.0003)
    
    g_x, g_y, g_xy = Graph(), Graph(), Graph()
    g_x.add_point(t, x1)
    g_y.add_point(t, x2)
    g_xy.add_point(x1, x2)

    x <= g_x.to_json()
    y <= g_y.to_json()
    xy <= g_xy.to_json()

    await x.deliver()
    await y.deliver()
    await xy.deliver()

    global next_store_time
    now = time.time()
    if now > next_store_time:
        datastore.update(g_x, tag='x')
        datastore.update(g_y, tag='y')
        datastore.update(g_xy, tag='xy')
        next_store_time = now + 5
    
    time.sleep(0.5)
