
from slowpy.mesh import Tasklet
tasklet = Tasklet(name='device_control')


from slowpy.control import control_system as ctrl
device = ctrl.import_control_module('DummyDevice').randomwalk_device()
device.is_running = False


@tasklet.loop(interval=1.0)
def loop():
    if not device.is_running:
        return
    
    data = device.ch(0).get()
    print(data)
        
    tasklet.mesh.publish('data.store.HV.ch0', {'V0': data})


#@tasklet.mesh.on('control.start')
@tasklet.mesh.export()
def start(params={}):
    print('start')
    device.is_running = True


@tasklet.mesh.on('control.stop')
def stop(params):
    device.is_running = False


    

if __name__ == '__main__':
    tasklet.run(slowdash_url='http://localhost:18881')
