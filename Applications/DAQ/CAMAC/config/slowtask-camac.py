
import sys, os, asyncio, time, json, copy, logging
from dataclasses import dataclass, asdict, is_dataclass
from slowpy.control import control_system as ctrl


#############################
"""
Common Run Control Structure
"""

@dataclass
class RunSettings:
    measurement: str = 'Camac'
    run_length: float = 0
    repeat: bool = False
    offline: bool = False
    run_number: int = 1   # current (if running) or next run number
run_settings = RunSettings()

        
@dataclass
class RunStatus:
    timestamp: float = 0
    run_name: str = '--'  # current (if running) or last run number
    running: bool = False
    start_time: float = 0
    lapse: float = 0
run_status = RunStatus()


def save_settings(name:str, settings):
    with open(f'{name}.json', 'w') as f:
        if is_dataclass(settings):
            json.dump(asdict(settings), f)
        else:
            try:
                json.dump(settings, f)
            except Exception as e:
                logging.error(f'unable to save settings: {name}: {e}')

        
def load_settings(name:str, settings=None):
    if not os.path.isfile(f'{name}.json'):
        return None
    try:
        with open(f'{name}.json') as f:
            doc = json.load(f)
    except Exception as e:
        logging.error(f'unable to load settings: {name}: {e}')
        return None

    if settings is None:
        return doc
    
    if isinstance(settings, dict):
        settings.clear()
        for k,v in doc.items():
            settings[k] = copy.deepcopy(v)
        
    else:
        # dataclass or class instance
        try:
            for k,v in doc.items():
                setattr(settings, k, v)
        except Exception as e:
            logging.error(f'unable to load settings: {name}: {e}')
        
    return settings


async def _initialize():
    load_settings('run_settings', run_settings)
    await do_initialize()

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
                run_settings.run_number = run_settings.run_number + 1
                save_settings('run_settings', run_settings)
                await ctrl.aio_stream('run_settings', run_settings)
            await start_run()
    elif now >= run_status.timestamp + 1:
        run_status.timestamp = now
        await ctrl.aio_stream('run_status', run_status)
        
    if run_status.running:
        await do_run_loop()
    

async def start(measurement:str, run_number:int, run_length:float, repeat:bool, offline:bool, **kwargs):
    if run_status.running:
        return False

    run_settings.measurement = measurement
    run_settings.run_number = int(run_number)
    run_settings.run_length = float(run_length)
    run_settings.repeat = repeat
    run_settings.offline = offline

    save_settings('run_settings', run_settings)
    await ctrl.aio_stream('run_settings', run_settings)
    
    try:
        await do_configure(**kwargs)
    except Exception as e:
        logging.error(e)
        return False

    if not await start_run():
        return False
    
    return True


async def stop(measurement:str, run_number:int, run_length:float, repeat:bool, offline:bool, **kwargs):
    if not run_status.running:
        return False
    
    result = await stop_run()

    run_settings.measurement = measurement
    run_settings.run_number = int(run_number)
    run_settings.run_length = float(run_length)
    run_settings.repeat = repeat

    if not run_settings.offline and run_settings.run_number > 0:   # use the offline setting of the current run
        run_settings.run_number = run_settings.run_number + 1
    run_settings.offline = offline    
        
    save_settings('run_settings', run_settings)
    await ctrl.aio_stream('run_settings', run_settings)

    # update the CAMAC settings stored in the stream cache
    try:
        await do_configure(**kwargs)
    except Exception as e:
        logging.error(e)
    
    return result

    
async def start_run():
    if run_status.running:
        return False
    
    run_status.run_name = f'{run_settings.measurement}.{run_settings.run_number:05d}'
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
camac = ctrl.camac(crate=1, dummy=True)

import slowpy as slp
rate_trend = slp.RateTrend(length=3600, tick=1)
histograms = {}
ts_store = slp.store.create_datastore_from_url('sqlite:///CamacTimeSeries.db', 'ts_data')
data_store = None


@dataclass
class ModuleConfig:
    name:str
    station:int
    channels:list[int]
    range_max: int

@dataclass
class CamacConfig:
    crate: int
    modules: list[ModuleConfig]
    lam_station: int
        
camac_config = CamacConfig(0, [], -1)
last_stream_time = 0


async def do_initialize():
    camac_settings = {}
    if load_settings('camac_settings', camac_settings) is not None:
        await ctrl.aio_stream('camac_settings', camac_settings)
        

async def do_configure(**args):
    save_settings('camac_settings', args)
    await ctrl.aio_stream('camac_settings', args)
    
    camac_config.crate = int(args.get('crate', 1))
    camac_config.modules = []
    camac_config.lam_station = 0
    
    for m in range(0, 20):
        if f'name{m}' in args:
            name = args.get(f'name{m}', f'module{m:02}')
            station = int(args.get(f'station{m}', 0))
            channels = [ ch for ch in range(0, 32) if args.get(f'm{m}_ch{ch}', False) ]
            range_max = int(args.get(f'range{m}', 4096))
            module = ModuleConfig(name, station, channels, range_max)
            camac_config.modules.append(module)
            
    lam = int(args.get('lam', -1))
    if lam >= 0 and lam < len(camac_config.modules):
        camac_config.lam_station = camac_config.modules[lam].station

            
async def do_run_start():
    print(f"CAMAC: starting a new run {run_status.run_name}")
    
    if not camac.open(camac_config.crate):
        return False
    
    global histograms
    data_fields = {}
    histograms = {}
    for module in camac_config.modules:
        for ch in module.channels:
            tag = f'{module.name}.ch{ch:02}'
            h = slp.Histogram(128, 0, module.range_max)
            h.add_stat(slp.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))
            histograms[f'hist_{tag}'] = h
            data_fields[tag] = int

    global data_store
    if not run_settings.offline and run_status.run_name:
        data_store = slp.store.DataStore_HDF5(
            f'{run_status.run_name}.hdf5',
            dataset = f'crate{camac_config.crate}',
            fields = data_fields,
            recreate = True,
        )
    else:
        data_store = None
            
    rate_trend.clear()

    global last_stream_time
    last_stream_time = 0

    return True

    
async def do_run_stop():
    print(f"CAMAC: stopping run {run_status.run_name}")
    camac.close()

    global data_store
    if data_store is not None:
        data_store.close()
        data_store = None

    return True

        
async def do_run_loop():
    if camac_config.lam_station > 0:
        camac.module(camac_config.lam_station).wait()
        
    timestamp = time.time()
    rate_trend.fill(timestamp)

    for module in camac_config.modules:
        for address in module.channels:
            tag = f'{module.name}.ch{address:02}'
            try:
                value = camac.module(module.station).channel(address).get()
            except Exception as e:
                logging.error(f'ERROR: CAMAC: {e}')
                continue
            
            histograms[f'hist_{tag}'].fill(value)
            if data_store is not None:
                data_store.append({tag: value}, timestamp=timestamp)

    for module in camac_config.modules:
        try:
            camac.module(module.station).clear()
        except Exception as e:
            logging.error(f'ERROR: CAMAC: {e}')
        
    global last_stream_time
    if timestamp >= last_stream_time + 1:
        last_stream_time = timestamp
        ts_store.append(rate_trend.timeseries(flush=True), tag='rate')
        #for tag, hist in histograms.items():
        #    await ctrl.aio_stream(tag, hist)


    
#############################


if __name__ == '__main__':
    async def main():
        await _initialize()
        await start(measurement='test', run_number=1, run_length=10, repeat=False, offline=False)
        
        ctrl.stop_by_signal()
        while not ctrl.is_stop_requested():
            await _loop()
            
        await stop()
        await _finalize()
        
    asyncio.run(main())
