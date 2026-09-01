
from slowpy.mesh import Tasklet, DataPacket
tasklet = Tasklet()

from slowpy.control import control_system as ctrl
device = ctrl.import_control_module('DummyDevice').randomwalk_device()
device.is_running = False


@tasklet.initialize()
async def initialize():
    await tasklet.mesh.registry.aio_set('setup/run/status', 'initialized')

    
@tasklet.loop(interval=0.5)
def loop():
    if not device.is_running:
        return
    
    data = device.ch(0).get()
    print(data)
        
    tasklet.mesh.publish('data.store', DataPacket(data, tag='HV.ch0.V'))


@tasklet.mesh.export
def set_value(value:float):
    print(f'set: {value}')
    device.ch(0).set(value)

    
@tasklet.mesh.on('control.start')
async def start(params):
    print(f'start: {params}')
    device.is_running = True
    await tasklet.mesh.registry.aio_set('setup/run/status', 'running')


@tasklet.mesh.on('control.stop')
async def stop(params):
    print(f'stop: {params}')
    device.is_running = False
    await tasklet.mesh.registry.aio_set('setup/run/status', 'idle')


    
if __name__ == '__main__':
    tasklet.run(slowdash_url='http://localhost:18881')
