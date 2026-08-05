
import sys, os, asyncio, time, json, logging
from dataclasses import dataclass, asdict
from slowpy.control import control_system as ctrl


#############################
"""
Common Run Control Structure
"""

@dataclass
class RunSettings:
    run_name: str = 'Run'
    run_number: int = 1
    run_length: float = 0
    repeat: bool = False
    offline: bool = False
run_settings = RunSettings()

        
@dataclass
class RunStatus:
    timestamp: float = 0
    running: bool = False
    start_time: float = 0
    lapse: float = 0
run_status = RunStatus()


def save_run_settings():
    with open('run_settings.json', 'w') as f:
        json.dump(asdict(run_settings), f)

        
def load_run_settings():
    if not os.path.isfile('run_settings.json'):
        return
    try:
        with open('run_settings.json') as f:
            for k,v in json.load(f).items():
                setattr(run_settings, k, v)
    except Exception as e:
        logging.error(e)
        
    
async def _initialize():
    load_run_settings()

    now = time.time()
    run_status.timestamp = now
    await ctrl.aio_stream('run_settings', run_settings)
    await ctrl.aio_stream('run_status', run_status)


async def _finalize():
    pass


async def _loop():    
    if not run_status.running:
        await asyncio.sleep(0.1)
        return
        
    now = time.time()
    run_status.lapse = round(now - run_status.start_time, 3)
    if run_settings.run_length > 0 and run_status.lapse >= run_settings.run_length:
        await stop_run()
        if run_settings.repeat:
            if not run_settings.offline and run_settings.run_number > 0:
                run_settings.run_number += 1
                save_run_settings()
                await ctrl.aio_stream('run_settings', run_settings)
            await start_run()
    elif now >= run_status.timestamp + 1:
        run_status.timestamp = now
        await ctrl.aio_stream('run_status', run_status)
        
    if run_status.running:
        await do_run_loop()
    

async def start(run_name:str, run_number:int, run_length:float, repeat:bool, offline:bool, **kwargs):
    if run_status.running:
        return False

    run_settings.run_name = run_name
    run_settings.run_number = int(run_number)
    run_settings.run_length = float(run_length)
    run_settings.repeat = repeat
    run_settings.offline = offline

    save_run_settings()
    await ctrl.aio_stream('run_settings', run_settings)
    
    try:
        await do_configure(**kwargs)
    except Exception as e:
        logging.error(e)
        return False

    if not await start_run():
        return False
    
    return True


async def stop(run_name:str, run_number:int, run_length:float, repeat:bool, offline:bool, **kwargs):
    if not run_status.running:
        return False
    
    result = await stop_run()

    run_settings.run_name = run_name
    run_settings.run_number = int(run_number)
    run_settings.run_length = float(run_length)
    run_settings.repeat = repeat
    run_settings.offline = offline    
    if not run_settings.offline and run_settings.run_number > 0:
        run_settings.run_number += 1
        
    await ctrl.aio_stream('run_settings', run_settings)
    save_run_settings()
        
    return result

    
async def start_run():
    if run_status.running:
        return False
    
    if not await do_run_start():
        return False

    now = time.time()
    run_status.timestamp = now
    run_status.running = True
    run_status.start_time = now
    run_status.lapse = 0
    await ctrl.aio_stream('run_status', run_status)

    return True
    

async def stop_run():
    if not run_status.running:
        return False
    
    now = time.time()
    run_status.timestamp = now
    run_status.running = False
    await ctrl.aio_stream('run_status', run_status)
    
    if not await do_run_stop():
        pass
    
    return True


#############################
"""
Measurement Specific Stuff
"""

ctrl.import_control_module('CAMAC')
camac = ctrl.camac(crate=1, dummy=False)

import slowpy as slp
rate_trend = slp.RateTrend(length=300, tick=1)
histograms = {}
data_store = None


@dataclass
class ModuleSettings:
    name:str
    station:int
    channels:list[int]
    range_max: int

@dataclass
class CamacSettings:
    crate: int
    modules: list[ModuleSettings]
    lam_station: int
        
camac_settings = CamacSettings(0, [], -1)
last_stream_time = 0
        

async def do_configure(**args):
    camac_settings.crate = int(args.get('crate', 1))
    camac_settings.modules = []
    camac_settings.lam_station = 0
    
    for m in range(0, 20):
        if f'name{m}' in args:
            name = args.get(f'name{m}', f'module{m:02}')
            station = int(args.get(f'station{m}', 0))
            channels = [ ch for ch in range(0, 32) if args.get(f'm{m}_ch{ch}', False) ]
            range_max = int(args.get(f'range{m}', 4096))
            module = ModuleSettings(name, station, channels, range_max)
            camac_settings.modules.append(module)
            
    lam = int(args.get('lam', -1))
    if lam >= 0 and lam < len(camac_settings.modules):
        camac_settings.lam_station = camac_settings.modules[lam].station

            
async def do_run_start():
    print(f"CAMAC: starting a new run {run_settings.run_number}")
    
    if not camac.open(camac_settings.crate):
        return False
    
    global histograms
    data_fields = {}
    histograms = {}
    for module in camac_settings.modules:
        for ch in module.channels:
            tag = f'{module.name}.ch{ch:02}'
            h = slp.Histogram(128, 0, module.range_max)
            h.add_stat(slp.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))
            histograms[f'hist_{tag}'] = h
            data_fields[tag] = int

    global data_store
    if run_settings.run_number > 0:
        file_name = f'{run_settings.run_name}{run_settings.run_number:05d}.hdf5'
    elif len(run_settings.run_name) > 0:
        file_name = f'{run_settings.run_name}.hdf5'
    else:
        file_name = f'data.hdf5'
    data_store = slp.store.DataStore_HDF5(
        file_name,
        dataset = f'crate{camac_settings.crate}',
        fields = data_fields,
        recreate = True,
    )
            
    rate_trend.clear()

    global last_stream_time
    last_stream_time = 0

    return True

    
async def do_run_stop():
    print(f"CAMAC: stopping run {run_settings.run_number}")
    camac.close()

    global data_store
    if data_store is not None:
        data_store.close()
        data_store = None

    return True

        
async def do_run_loop():
    if camac_settings.lam_station > 0:
        camac.module(camac_settings.lam_station).wait()
        
    timestamp = time.time()
    rate_trend.fill(timestamp)

    for module in camac_settings.modules:
        for address in module.channels:
            tag = f'{module.name}.ch{address:02}'
            try:
                value = camac.module(module.station).channel(address).get()
            except Exception as e:
                logging.error(f'ERROR: CAMAC: {e}')
                continue
            
            histograms[f'hist_{tag}'].fill(value)
            data_store.append({tag: value}, timestamp=timestamp)

    for module in camac_settings.modules:
        try:
            camac.module(module.station).clear()
        except Exception as e:
            logging.error(f'ERROR: CAMAC: {e}')
        
    global last_stream_time
    if timestamp >= last_stream_time + 1:
        await ctrl.aio_stream('rate_trend', rate_trend.timeseries())
        for tag, hist in histograms.items():
            await ctrl.aio_stream(tag, hist)
        last_stream_time = timestamp


    
#############################


if __name__ == '__main__':
    async def main():
        await _initialize()
        await start(run_name='test', run_number=1, run_length=10, repeat=False, offline=False)
        
        ctrl.stop_by_signal()
        while not ctrl.is_stop_requested():
            await _loop()
            
        await stop()
        await _finalize()
        
    asyncio.run(main())
