
import sys, os, asyncio, time, json, logging
from dataclasses import dataclass, asdict
from slowpy.control import control_system as ctrl

@dataclass
class RunSetting:
    run_number: int = 1
    stop_after: bool = False
    run_length: int = 3600
    repeat: bool = False
    offline: bool = False
run_setting = RunSetting()
        
@dataclass
class RunStatus:
    running: bool = False
    start_time: float = 0
    lapse: float = 0
run_status = RunStatus()


def save_run_setting():
    with open('run_run_setting.json', 'w') as f:
        json.dump(asdict(run_setting), f)

        
def load_run_setting():
    if not os.path.isfile('run_run_setting.json'):
        return
    try:
        with open('run_run_setting.json') as f:
            for k,v in json.load(f).items():
                setattr(run_setting, k, v)
    except Exception as e:
        logging.error(e)


async def stream_status():
    await ctrl.aio_stream('run_setting', run_setting)
    await ctrl.aio_stream('run_status', run_status)
        
    
async def _initialize():
    load_run_setting()
    await stream_status()


async def _finalize():
    pass


async def _loop():    
    if not run_status.running:
        await ctrl.aio_sleep(0.1)
        return

    run_status.lapse = round(time.time() - run_status.start_time,3)
    await stream_status()

    if run_setting.stop_after and run_status.lapse >= run_setting.run_length:
        await stop()
        if run_setting.repeat:
            await start()
            
    if run_status.running:
        await do_run_loop()


async def start(run_number:int=None, stop_after:bool=None, run_length:float=None, repeat: bool=None, offline:bool=None):
    if run_number is not None:
        run_setting.run_number = run_number
    if stop_after is not None:
        run_setting.stop_after = stop_after
    if run_length is not None:
        run_setting.run_length = run_length
    if repeat is not None:
        run_setting.repeat = repeat
    if offline is not None:
        run_setting.offline = offline

    save_run_setting()
    
    run_status.start_time = round(time.time(),3)
    run_status.running = True
    await stream_status()
    
    await do_run_start()
    
    return True


async def stop():
    run_status.running = False
    await do_run_stop()
    
    if not run_setting.offline:
        run_setting.run_number += 1
        
    save_run_setting()
    await stream_status()
    
    return True


#############################
"""
Measurement Specific Stuff
"""

ctrl.import_control_module('CAMAC')
camac = ctrl.camac(crate=1, dummy=False)
modules = []
lam_module = None

import slowpy as slp
rate_trend = slp.RateTrend(length=300, tick=1)
values_hist = slp.Histogram(128, 0, 2048);
values_hist.add_stat(slp.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))
last_stream_time = 0


async def do_run_start():
    print(f"starting a new run {run_setting.run_number}")
    rate_trend.clear()
    values_hist.clear()

    global modules, lam_module
    modules = []
    modules.append(camac.module(station = 3))
    lam_module = modules[0]
    
    
async def do_run_stop():
    rate_trend.clear()
    values_hist.clear()

    
async def do_run_loop():
    if lam_module is not None:
        lam_module.wait()
        
    timestamp = time.time()
    rate_trend.fill(timestamp)

    for address in range(0, 2):
        try:
            value = modules[0].channel(address).get()
        except Exception as e:
            logging.error(f'ERROR: CAMAC: {e}')
            continue
        values_hist.fill(value)

    for module in modules:
        module.clear()
        
    global last_stream_time
    if timestamp >= last_stream_time + 1:
        await ctrl.aio_stream('rate_trend', rate_trend.timeseries())
        await ctrl.aio_stream('values_hist', values_hist)
        last_stream_time = timestamp


    
#############################


if __name__ == '__main__':
    async def main():
        await _initialize()
        await start()
        ctrl.stop_by_signal()
        while not ctrl.is_stop_requested():
            await _loop()
        await stop()
        await _finalize()
    asyncio.run(main())
