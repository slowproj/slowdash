import asyncio
from slowpy.mesh import Tasklet, DataPacket
tasklet = Tasklet()

from slowpy.control import control_system as ctrl
device = ctrl.import_control_module('DummyDevice').randomwalk_device()
device.is_running = False


@tasklet.initialize()
async def initialize():
    await tasklet.mesh.registry.aio_set('setup/run/status', 'initialized')

    
@tasklet.loop(interval=0.5)
async def loop():
    if not device.is_running:
        return
    
    data = await device.ch(0).aio_get()
    print(data)
        
    await tasklet.mesh.aio_publish(DataPacket(data, tag='HV.ch0.V').to('data.store'))


@tasklet.mesh.export()
async def set_value(V0_setpoint:float):
    print(f'set: {V0_setpoint}')
    device.ch(0).set(V0_setpoint)

    
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
    tasklet.run(mesh_url='slowmq://localhost:18881')
