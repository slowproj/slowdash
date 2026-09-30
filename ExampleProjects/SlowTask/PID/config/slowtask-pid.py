from slowpy.mesh import Tasklet
tasklet = Tasklet()

from slowpy.control import control_system as ctrl
plant = ctrl.import_control_module('DummyDevice').first_order_plant(gain=0.1, noise=0.1)
plant.start()

import slowpy.store
datastore = slowpy.store.create_datastore_from_url('sqlite:///SlowData.db', 'numeric_data')
datastore_obj = datastore.another('object_data')

import logging

pid = None

@tasklet.initialize()
async def initialize():
    logging.error("hello from PID")
    # Making the browser input values and internal parameter values consistent #
    if True:
        # Browsers to internals: initial PID parameters from the last browser inputs
        form = await ctrl.form('pid_setup').aio_get()   # form is a Python dict
        Kp = form.get('Kp', 1)
        Ki = form.get('Ki', 1)
        Kd = form.get('Kd', 0)
        limits_low = form.get('limits_low', -100)
        limits_high = form.get('limits_high', 100)
    else:
        # Internals to browsers: fixed initial PID parameters; send them to the browser inputs
        Kp, Ki, Kd = 1, 1, 0
        limits_low, limits_high = -100, 100
        await ctrl.form('pid_setup').aio_set({
            'Kp': Kp, 'Ki': Ki,'Kd': Kd,
            'limits_low': limits_low, 'limits_high': limits_high
        })
    
    global pid
    pid = plant.control().pid(plant.state(), Kp=Kp, Ki=Ki, Kd=Kd, output_limits=(limits_low, limits_high))

    
@tasklet.loop(interval=1)
def loop():
    control = float(plant.control().get())
    state = float(plant.state().get())
    status = pid.status().get()

    datastore.append({'control': control, 'state': state})
    datastore_obj.append({'pid_status': {'tree': status}})
    datastore_obj.append({'true': True})
    if status.get('running', False):
        datastore.append({ f'pid_{k}':v for k,v in status.items() if isinstance(v, float)})
        
    
@tasklet.mesh.export()
def set(Kp:float, Ki:float, Kd:float, limits_low:float, limits_high:float):
    pid.do_configure(Kp=Kp, Ki=Ki, Kd=Kd, output_limits=(limits_low, limits_high))
    

@tasklet.mesh.export()
def start(setpoint:float):
    pid.set(setpoint)
    ctrl.stream('pid_status', pid.status().get())
    

@tasklet.mesh.export()
def stop():
    pid.set(None)
    ctrl.stream('pid_status', pid.status().get())
    

@tasklet.mesh.export()
def set_output(output:float):
    pid.set(None)
    plant.control().set(output)
    ctrl.stream('pid_status', pid.status().get())
    

    
@tasklet.content('config/html-pid_control.html')
def html_control():
    return '''
      <form name="pid_control">
        <table>
          <tr><th>PID Setpoint</th>
            <td><input type="number" name="setpoint" step="any" value="0" style="width:8em"></td>
            <td>
              <button name="pid.start()">Set</button>
              <button name="pid.stop()" sd-enabled="pid_status['running']">Stop</button>
            </td>
          </tr>
          <tr><th>Manual Output</th>
            <td><input type="number" name="output" step="any" value="0" style="width:8em"></td>
            <td><button name="pid.set_output()">Set</button></td>
          </tr>
        </table>
      </form>
    '''
    
@tasklet.content('config/html-pid_setup.html')
def html_setup():
    return '''
      <form name="pid_setup">
        <table>
          <tr><th>Loop Parameters</th>
            <td>
              Kp: <input type="number" name="Kp" step="any" value="1.0" style="width:5em">
              Ki: <input type="number" name="Ki" step="any" value="1.0" style="width:5em">
              Kd: <input type="number" name="Kd" step="any" value="0.0" style="width:5em">
            </td>
            <td></td>
          </tr>
          <tr><th>Output Limits</th>
            <td>
              Low: <input type="number" name="limits_low" step="any" value="-10.0" style="width:5em">
              High: <input type="number" name="limits_high" step="any" value="10.0" style="width:5em">
            </td>
            <td></td>
          </tr>
          <tr><th></th><td></td><td><button name="pid.set()">Set</button></td>
        </table>
      </form>
    '''
    
    
if __name__ == '__main__':
    tasklet.run()
