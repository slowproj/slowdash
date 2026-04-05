

from slowpy.control import control_system as ctrl
mic = ctrl.import_control_module('Microphone').microphone(block_size=1024)
mic.is_running = False

from slowpy import Graph


async def _initialize():
    mic.stop()
    mic.is_running = False
    await ctrl.aio_publish(mic.is_running, name='mic_running')

    
async def _finalize():
    mic.stop()
    mic.is_running = False
    await ctrl.aio_publish(mic.is_running, name='mic_running')


async def _loop():
    while not ctrl.is_stop_requested():
        if not mic.is_running:
            await ctrl.aio_sleep(0.1)
            continue

        data = await mic.data().aio_get()
        rms = data.rms().get()
        x, y = data.trace().get()
        f, fft = data.fft().get()

        g_trace, g_fft = Graph(), Graph()
        g_trace.add_point(x, y)
        g_fft.add_point(f, fft)
        
        await ctrl.aio_publish(rms, name='mic')
        await ctrl.aio_publish(g_trace, name='mic_trace')
        await ctrl.aio_publish(g_fft, name='mic_fft')
        
        await ctrl.aio_sleep(0.5)


async def start(sample_rate:int, block_size:int):
    mic.stop()
    mic.sample_rate().set(sample_rate)
    mic.block_size().set(block_size)
    mic.start()
    mic.is_running = True
    await ctrl.aio_publish(mic.is_running, name='mic_running')
    

async def stop():
    mic.is_running = False
    mic.stop()
    await ctrl.aio_publish(mic.is_running, name='mic_running')
    

        

if __name__ == '__main__':
    from slowpy.mesh import Tasklet
    Tasklet().run()
