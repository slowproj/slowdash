
from slowpy.mesh import Tasklet, DataPacket
tasklet = Tasklet()

from slowpy import Histogram
histograms = {}
is_running = False

@tasklet.mesh.on('data.*.HV.>')
def process_data(headers, body):
    if not is_running:
        return
    
    for channel, data in body.items():
        if channel not in histograms:
            print(f'creating a histogram for channel {channel}')
            histograms[channel] = Histogram(100, -50, 50)
        histograms[channel].fill(data.get('x', []))


@tasklet.loop(interval=1)
def stream_hist():
    if not is_running:
        return
    
    for channel, hist in histograms.items():
        tasklet.mesh.publish('data.stream', DataPacket(hist, tag=f'histogram.{channel}'))


@tasklet.mesh.on('control.start')
async def start():
    global is_running, histograms
    is_running = True
    histograms = {}


@tasklet.mesh.on('control.stop')
async def stop():
    global is_running
    is_running = False


    
    
#### Standalone Execution  ####
    
if __name__ == '__main__':
    tasklet.run(slowdash_url='http://localhost:18881')
