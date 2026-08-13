
import time, logging
from dataclasses import dataclass
import slowpy.store 
from slowpy.control import control_system as ctrl
labjack = None
datastore = None


@dataclass
class RunStatus:
    running: bool = False
    readout_interval: float = 1
    last_readout_time: float = 0
run_status = RunStatus()


async def _initialize():
    global labjack
    ctrl.import_control_module('LabJackU')
    labjack = ctrl.labjack_U3(fio_config=0x0f)

    config = labjack.config().get()
    await ctrl.aio_stream('labjack_config', config)
    await ctrl.aio_stream('run_status', run_status)

    global datastore
    datastore = slowpy.store.create_datastore_from_url('sqlite:///SlowDataStore.db', 'ts_data')

    
async def _loop():
    if not run_status.running:
        await ctrl.aio_sleep(0.1)
        return
        
    now = time.monotonic()
    if now < run_status.last_readout_time + run_status.readout_interval:
        await ctrl.aio_sleep(0.01)
        return
    else:
        run_status.last_readout_time = now
        
    for ch in range(4):
        ain = labjack.ain(ch).get()
        datastore.append(ain, tag='ain%02d'%ch)


async def start(readout_interval:float):
    run_status.readout_interval = readout_interval
    run_status.last_readout_time = 0
    run_status.running = True
    await ctrl.aio_stream('run_status', run_status)
    

async def stop():
    run_status.running = False
    await ctrl.aio_stream('run_status', run_status)
    

def _get_html():
    return '''
    <h3>Run Control</h3>
    <form>
      Readout Inerval (s): <input type="number" step="0.1" name="readout_interval" value="1">
      <p>
      <div style="font-size:150%">
        <input type="submit" name="labjack.start()" value="Start" sd-enabled="run_status['running']->invert()">
        <input type="submit" name="labjack.stop()" value="Stop" sd-enabled="run_status['running']">
      </div>
    </form>
    '''
        

    
if __name__ == '__main__':
    logging.basicConfig(loglevel=logging.DEBUG)
    async def main():
        await _initialize()
        start(readout_interval=0.5)
        while True:
            await _loop()

    import asyncio
    asyncio.run(main())
