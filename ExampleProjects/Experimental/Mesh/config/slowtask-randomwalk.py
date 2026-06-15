
from slowpy.mesh import Tasklet
tasklet = Tasklet()

from slowpy.control import control_system as ctrl
device = ctrl.import_control_module('DummyDevice').randomwalk_device()
device.is_running = False



@tasklet.loop(interval=1.0)
async def loop():
    if not device.is_running:
        return
    
    data = device.ch(0).get()
    print(data)
        
    await tasklet.mesh.aio_publish('data.store.HV.ch0', {'V0': data})


@tasklet.mesh.export
def set_value(value:float):
    print(f'set: {value}')
    device.ch(0).set(value)

    
@tasklet.mesh.on('control.start')
def start(params={}):
    print('start')
    device.is_running = True


@tasklet.mesh.on('control.stop')
def stop(params):
    print(f'stop: {params}')
    device.is_running = False


@tasklet.mesh.on('control.>')
def a(headers, body):
    print(f'Headers: {headers}, Body: {body}')

    

if __name__ == '__main__':
    tasklet.run(slowdash_url='http://localhost:18881')
