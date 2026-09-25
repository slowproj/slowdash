
import sys, os, asyncio, time, json, logging
from dataclasses import dataclass, asdict

import slowpy
from slowpy.control import control_system as ctrl
tasklet = slowpy.mesh.Tasklet()


@dataclass
class RunStatus:
    run_number: int = 1
    stop_after: bool = False
    run_length: int = 3600
    repeat: bool = False
    offline: bool = False
    running: bool = False
    start_time: float = 0
    lapse: float = 0
run_status = RunStatus()


@tasklet.loop(interval=0.1, ticks={'readout':1, 'stream':10})
async def _loop(ticks):    
    if ticks.stream:
        if run_status.running:
            run_status.lapse = round(time.time() - run_status.start_time,3)
        await ctrl.aio_stream('run_status', run_status)

    if not run_status.running:
        return
    
    if run_status.stop_after and run_status.lapse >= run_status.run_length:
        await stop()
        if run_status.repeat:
            await start()
            
    await do_run_loop(ticks)


@tasklet.mesh.export()
async def start(run_number:int=None, stop_after:bool=None, run_length:float=None, repeat: bool=None, offline:bool=None):
    if run_number is not None:
        run_status.run_number = run_number
    if stop_after is not None:
        run_status.stop_after = stop_after
    if run_length is not None:
        run_status.run_length = run_length
    if repeat is not None:
        run_status.repeat = repeat
    if offline is not None:
        run_status.offline = offline

    run_status.start_time = round(time.time(),3)
    run_status.running = True
    
    await ctrl.aio_stream('run_status', run_status)
    print(f"starting a new run {run_status.run_number}")

    await do_run_start()
    
    return True


@tasklet.mesh.export()
async def stop():
    run_status.running = False
    print(f"stopped run {run_status.run_number}")
    
    await do_run_stop()
    
    if not run_status.offline:
        run_status.run_number += 1
        await tasklet.mesh.aio_publish('form.input.run_control.run_number', {
            'form': 'run_control',
            'element': 'run_number',
            'value': run_status.run_number,
        })        
        
    await ctrl.aio_stream('run_status', run_status)
    
    return True


@tasklet.content('config/html-run_control.html')
def html():
    return '''
      <h3>Run Control</h3>
      <form name="run_control">
        Run Number: <input name="run_number" type="number" step="1" value="0" style="width:6em">,
        or <input type="checkbox" name="offline"]> Offline Run
        <span style="font-size:80%">(file not saved, run number not incremented)</span>
        <br>
        <input type="checkbox" name="stop_after"> Stop after
        <input type="number" name="run_length" value="0" style="width:6em"> s, 
        <input type="checkbox" name="repeat"]> Then Repeat<br>
        <p>
        <div style="font-size:150%">
          <input type="submit" name="run_control.start()" value="Start" sd-enabled="run_status['running']->invert()" sd-confirm="Are you ready to start?">
          <input type="submit" name="run_control.stop()" value="Stop" sd-enabled="run_status['running']">
        </div>
      </form>
    '''    



#############################
"""
Measurement Specific Stuff
- Readout: dummy event generator
- Storage: HDF5 (one file for each run)
- Analysis:
  - run lapse
  - trigger rate (rate trend graph)
  - number-of-hits distribution (nhits histogram)
"""

n_channels = 16
data_fields = {
    **{ f'tdc{ch:02d}':int for ch in range(n_channels) },
    **{ f'adc{ch:02d}':int for ch in range(n_channels) },
}

ctrl.import_control_module('DummyDevice')
device = ctrl.random_event_device(rate=10, n=n_channels)
print("Dummy event generator loaded")


rate_trend = slowpy.RateTrend(length=300, tick=1)
nhits_hist = slowpy.Histogram(16, 0, 16);
nhits_hist.add_stat(slowpy.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))

datastore = None


async def do_run_start():
    rate_trend.clear()
    nhits_hist.clear()

    global datastore
    datastore = slowpy.store.DataStore_HDF5(
        f'run{run_status.run_number:05d}.hdf5',
        dataset='test',
        fields = data_fields,
        recreate = True,
    )
    
    device.do_start()

    
async def do_run_stop():
    global datastore
    
    if datastore:
        datastore.close()
        datastore = None

    rate_trend.clear()
    nhits_hist.clear()

    
async def do_run_loop(ticks):
    global datastore

    if ticks.readout:
        events = device.get()
        for i, ev in enumerate(events):
            timestamp = ev['timestamp']
            hits = ev['hits']
            n_hits = len([ch for ch in hits if ch.startswith('adc')])
        
            if datastore:
                datastore.append(hits, timestamp=timestamp)

            rate_trend.fill(timestamp)
            nhits_hist.fill(n_hits)


    if ticks.stream:
        await ctrl.aio_stream('rate_trend', rate_trend.timeseries())
        await ctrl.aio_stream('nhits_hist', nhits_hist)

    
#############################


if __name__ == '__main__':
    tasklet.run()
