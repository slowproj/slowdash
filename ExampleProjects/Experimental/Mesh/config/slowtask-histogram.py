
from slowpy.mesh import Tasklet, DataPacket
tasklet = Tasklet()

from slowpy import Histogram
histograms = {}
updated = False


@tasklet.mesh.on('data.*.HV.>')
def process_data(headers, body):
    for channel, data in body.items():
        if channel not in histograms:
            print(f'creating a histogram for channel {channel}')
            histograms[channel] = Histogram(100, -50, 50)
        histograms[channel].fill(data.get('x', []))

    global updated
    updated = True

    
@tasklet.loop(interval=1)
def stream_hist():
    global updated
    if not updated:
        return
    updated = False
    
    for channel, hist in histograms.items():
        tasklet.mesh.publish('data.stream', DataPacket(hist, tag=f'histogram.{channel}'))


@tasklet.mesh.on('control.start')
async def start():
    for h in histograms.values():
        h.clear()
    
    global updated
    updated = True
    


    
#### Standalone Execution  ####
    
if __name__ == '__main__':
    tasklet.run(slowdash_url='http://localhost:18881')
