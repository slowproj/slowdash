import slowpy

tasklet = slowpy.mesh.Tasklet()
histogram = slowpy.Histogram(nbins=20, range_min=-10, range_max=10)

    
@tasklet.mesh.on('data.store.>')
async def process_data(data: slowpy.mesh.DataPacket):
    for ch, value in data.values.items():
        if ch == 'volt':
            histogram.fill(value)


@tasklet.loop(interval=1)
async def stream_result():
    await tasklet.mesh.aio_publish('data.stream', slowpy.mesh.DataPacket(histogram, tag='hist01'))


@tasklet.mesh.on('mydaq.control.start')
async def clear():
    histogram.clear()
