
from slowpy.mesh import Tasklet
tasklet = Tasklet()

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


@tasklet.mesh.export
def set_value(value:float):
    print(f'set: {value}')
    device.ch(0).set(value)

    
@tasklet.mesh.on('control.start')
async def start(params):
    print(f'start: {params}')
    device.is_running = True
    print(await tasklet.mesh.registry.aio_get('randomwalk/run/status'))
    await tasklet.mesh.registry.aio_set('randomwalk/run/status', 'running')


@tasklet.mesh.on('control.stop')
async def stop(params):
    print(f'stop: {params}')
    device.is_running = False
    print(await tasklet.mesh.registry.aio_get('randomwalk/run/status'))
    await tasklet.mesh.registry.aio_set('randomwalk/run/status', 'idle')


    
if __name__ == '__main__':
    tasklet.run(slowdash_url='http://localhost:18881')
