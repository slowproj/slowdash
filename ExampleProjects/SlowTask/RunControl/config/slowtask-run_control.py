
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
        
@dataclass
class RunStatus:
    running: bool = False
    start_time: float = 0
    lapse: float = 0
        
run_setting, run_status = RunSetting(), RunStatus()
ctrl.export(run_setting, name='run_setting')
ctrl.export(run_status, name='run_status')


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

    
async def _initialize():
    load_run_setting()


async def _finalize():
    pass
    

async def _loop():    
    if not run_status.running:
        await ctrl.aio_sleep(0.1)
        return

    run_status.lapse = round(time.time() - run_status.start_time,3)
    await ctrl.aio_publish(run_status)

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
    await ctrl.aio_publish(run_setting)
    await ctrl.aio_publish(run_status)
    
    await do_run_start()
    
    return True


async def stop():
    run_status.running = False
    await do_run_stop()
    
    if not run_setting.offline:
        run_setting.run_number += 1
        
    save_run_setting()
    await ctrl.aio_publish(run_setting)
    await ctrl.aio_publish(run_status)
    
    return True


#############################
"""
Measurement Specific Stuff
- Readout: dummy event generator
- Analysis:
  - run lapse
  - trigger rate (rate trend graph)
  - number-of-hits distribution (nhits histogram)
"""

ctrl.import_control_module('DummyDevice')
device = ctrl.random_event_device(rate=10)
print("Dummy event generator loaded")

import slowpy as slp
rate_trend = slp.RateTrend(length=10, tick=0.2)
nhits_hist = slp.Histogram(16, 0, 16);
nhits_hist.add_stat(slp.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))


async def do_run_start():
    print(f"starting a new run {run_setting.run_number}")
    rate_trend.clear()
    nhits_hist.clear()
    device.do_start()

    
async def do_run_stop():
    rate_trend.clear()
    nhits_hist.clear()

    
async def do_run_loop():
    events = device.get()

    for ev in events:
        t = ev['timestamp']
        hits = ev['hits']
        tdc = {ch:value for ch,value in hits.items() if ch.startswith('tdc')}
        adc = {ch:value for ch,value in hits.items() if ch.startswith('adc')}
        nhits = len(adc)

        rate_trend.fill(t)
        nhits_hist.fill(nhits)

    await ctrl.aio_publish(rate_trend, 'rate_trend')
    await ctrl.aio_publish(nhits_hist, 'nhits_hist')

    await ctrl.aio_sleep(0.5)


    
#############################


if __name__ == '__main__':
    async def main():
        await _initialize()
        ctrl.stop_by_signal()
        run_status.running = True
        while not ctrl.is_stop_requested():
            await _loop()
        await _finalize()
    asyncio.run(main())
