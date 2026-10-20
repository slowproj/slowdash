import time
from dataclasses import dataclass

@dataclass
class RunStatus:
    auto_stop: bool = False
    run_length: float = 0
    start_time: float = 0
    running: bool = False
run_status = RunStatus()


from slowpy.control import control_system as ctrl
device = ctrl.ethernet('192.168.1.34', 5025).scpi()

import slowpy
tasklet = slowpy.mesh.Tasklet()


@tasklet.loop(interval=1)
async def loop():
    if run_status.running:
        try:
            volt = float(device.command('MEAS:VOLT:DC?').get() or 'nan')
            await tasklet.mesh.aio_publish(slowpy.mesh.DataPacket({'volt': volt}).to('data.store'))
        except Exception as e:
            print(f'ERROR: {e}')
            
        if run_status.auto_stop:
            now = time.time()
            if now - run_status.start_time >= run_status.run_length:
                run_status.running = False

    ctrl.stream('run_status', run_status)


@tasklet.mesh.export()
async def start(auto_stop:bool, run_length:float):
    run_status.auto_stop = auto_stop
    run_status.run_length = run_length

    await tasklet.mesh.aio_publish('mydaq.control.start', {})
    
    run_status.start_time = time.time()
    run_status.running = True
    

@tasklet.mesh.export()
async def stop():
    run_status.running = False


@tasklet.content('config/html-testdaq.html')
async def html():
    return '''
      <form name="testdaq">
        <input type="checkbox" name="auto_stop">Stop After:
        <input type="number" name="run_length" value="10">
        <br>
        <input type="submit" name="read.start()" value="Start" sd-enabled="run_status['running']->invert()">
        <input type="submit" name="read.stop()" value="Stop" sd-enabled="run_status['running']">
      </form>
    '''
