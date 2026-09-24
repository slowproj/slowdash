from slowpy.mesh import Tasklet
tasklet = Tasklet()

from slowpy.control import control_system as ctrl
plant = ctrl.import_control_module('DummyDevice').second_order_plant()

Kp, Ki, Kd = 1, 0, 0
pid = plant.control().pid(plant.state(), Kp, Ki, Kd)

import slowpy.store
datastore = slowpy.store.create_datastore_from_url('sqlite:///SlowTaskTest.db', 'test')


@tasklet.initialize()
def initialize():
    plant.start()


@tasklet.loop(interval=1)
def loop():
    control = float(plant.control().get())
    state = float(plant.state().get())
    pid_status = pid.status().get()
    datastore.append({'pid_status': pid_status, 'control': control, 'state': state})
    

@tasklet.mesh.export()
def set(Kp:float, Ki:float, Kd:float):
    pid.do_configure(Kp, Ki, Kd)
    

@tasklet.mesh.export()
def start(target:float):
    pid.set(target)
    

@tasklet.mesh.export()
def stop(target:float):
    pid.set(None)
    

    
@tasklet.content('config/html-pid.html')
def html():
    return '''
        <form name="pid">
    <h4>Configuration</h4>
        Kp: <input type="number" name="Kp" step="any" value="1.0" style="width:5em">
        Ki: <input type="number" name="Ki" step="any" value="0.0" style="width:5em">
        Kd: <input type="number" name="Kd" step="any" value="0.0" style="width:5em">
        <button name="pid.set()">Set</button>

    <h4>Operation</h4>
          Target: <input type="number" name="target" step="any" value="0" style="width:8em">
          <button name="pid.start()">Start</button>
          <button name="pid.stop()">Stop</button>
        </form>
    '''
    


    
    
if __name__ == '__main__':
    tasklet.run()
