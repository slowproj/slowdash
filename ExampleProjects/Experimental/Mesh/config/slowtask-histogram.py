
from slowpy.mesh import Tasklet, DataPacket
tasklet = Tasklet()

from slowpy import Histogram
histograms = {}
is_running = False


@tasklet.mesh.on('data.*.HV.>')
async def process_data(headers, body):
    if not is_running:
        return
    
    for channel, data in body.items():
        if channel not in histograms:
            print(f'creating a histogram for channel {channel}')
            histograms[channel] = Histogram(100, -50, 50)
        histograms[channel].fill(data.get('x', []))

    
@tasklet.loop(interval=1)
async def stream_hist():
    if not is_running:
        return
    
    for channel, hist in histograms.items():
        await tasklet.mesh.aio_publish('data.stream', DataPacket(hist, tag=f'histogram.{channel}'))


@tasklet.initialize()
async def initialize():
    global is_running
    is_running = (await tasklet.mesh.registry.aio_get('setup/run/status', 'dead') == 'running')
    

@tasklet.mesh.on('control.start')
async def start():
    for h in histograms.values():
        h.clear()
    
    global is_running
    is_running = True
    

@tasklet.mesh.on('control.stop')
async def stop():
    global is_running
    is_running = False
    


    
#### Standalone Execution  ####
    
if __name__ == '__main__':
    tasklet.run(mesh_url='slowmq://localhost:18881')
