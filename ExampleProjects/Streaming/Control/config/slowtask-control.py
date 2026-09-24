
from slowpy.mesh import Tasklet
tasklet = Tasklet()

from slowpy.control import control_system as ctrl

import numpy as np
from slowpy import Graph

fx, fy = 3.2, 2.0
t0 = 0


@tasklet.initialize()
async def initialize():
    global fx, fy
    prev_form_values = await tasklet.mesh.registry.aio_get('pubsub.form.input.control.>', {})
    fx = prev_form_values.get('fx', {}).get('value', fx)
    fy = prev_form_values.get('fy', {}).get('value', fy)
    
    
@tasklet.loop(interval=0.2)
async def loop():
    global t0

    t0 += 0.1
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

        
@tasklet.mesh.on('form.input.control.fx')
async def set_fx(form_input):
    global fx
    fx = form_input.get('value', fx)


@tasklet.mesh.on('form.input.control.fy')
async def set_fy(form_input):
    global fy
    fy = form_input.get('value', fy)


@tasklet.content('config/html-control.html')
def html():
    return '''
    <form name="control">
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
