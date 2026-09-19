
from slowpy.control import control_system as ctrl
from slowpy.mesh import Tasklet
tasklet = Tasklet()

from slowpy.store import DataStore_Redis
datastore = DataStore_Redis('redis://localhost/1')

import time
import numpy as np
from slowpy import Graph

fx, fy = 3.2, 2.0
t0 = 0


@tasklet.mesh.on('form.inputs.scope_control.>')
async def control(doc):
    global fx, fy
    fx = doc.get('values', {}).get('fx', fx)
    fy = doc.get('values', {}).get('fy', fy)


@tasklet.loop(interval=0.5, ticks=20)
async def loop(ticks):
    global t0

    t0 += 0.05
    t = np.linspace(0, 1, 100)
    x1 = np.random.normal(np.cos((t+t0)*float(fx)*6.28), 0.0003)
    x2 = np.random.normal(np.sin((t+t0)*float(fy)*6.28), 0.0003)
    
    g_x, g_y, g_xy = Graph(), Graph(), Graph()
    g_x.add_point(t, x1)
    g_y.add_point(t, x2)
    g_xy.add_point(x1, x2)

    await ctrl.aio_stream('fx.stream', fx)
    await ctrl.aio_stream('fy.stream', fy)
    await ctrl.aio_stream('x.stream', g_x)
    await ctrl.aio_stream('y.stream', g_y)
    await ctrl.aio_stream('xy.stream', g_xy)

    if ticks:
        datastore.update(g_x, tag='x')
        datastore.update(g_y, tag='y')
        datastore.update(g_xy, tag='xy')

        
@tasklet.content('config/html-control.html')
def html():
    return '''
    <form name="scope_control">
      <datalist id="markers">
        <option value="0.1"></option><option value="5"></option><option value="9.9"></option>
      </datalist>
      <table>
        <tr>
          <td>Fx</td>
          <td><input name="fx" type="range" min="0.1" max="9.9" step="0.1" list="markers"></td>
          <td><span sd-value="fx.stream" style="font-size:150%">---</span></td>
        </tr><tr>
          <td>Fy</td>
          <td><input name="fy" type="range" min="0.1" max="9.9" step="0.1" list="markers"></td>
          <td><span sd-value="fy.stream" style="font-size:150%">---</span></td>
        </tr>
      </table>
    </form>
    '''
