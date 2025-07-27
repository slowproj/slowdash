

import sys, os, asyncio, time, json, logging
from dataclasses import dataclass, asdict
from slowpy.control import control_system as ctrl, ValueNode
import slowpy.store as sls

ctrl.import_control_module('DummyDevice')
device = ctrl.randomwalk_device()
ch0, ch1, ch2, ch3 = [ device.ch(ch) for ch in range(4) ]

print("hello from run_control")

@dataclass
class Context:
    run_number: int = 1
    stop_after: bool = False
    run_length: int = 3600
    repeat: bool = False
    offline: bool = False
    running: bool = False
        
context = Context()

def save_context():
    with open('run_context.json', 'w') as f:
        json.dump(asdict(context), f)
            
def load_context():
    if not os.path.isfile('run_context.json'):
        return
    try:
        with open('run_context.json') as f:
            for k,v in json.load(f).items():
                setattr(context, k, v)
    except Exception as e:
        logging.error(e)


import numpy as np
import slowpy as slp
h = slp.Histogram(100, 0, 10)
h.add_attr('color', 'red')
h.add_stat(slp.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))
h.add_stat(slp.HistogramCountStat(0, 10))
for i in range(1000):
    h.fill(np.random.normal(5, 2))
ctrl.export(h, 'hist')


a = ctrl.value(0)
b = ctrl.value(0)
c = ctrl.value(0)
d = ctrl.value(0)

xxx = {'name': 'hello', 'value': 3460 }

ctrl.export(a, 'a')
ctrl.export(b, 'b')
ctrl.export(c, 'c')
ctrl.export(d, 'd')
ctrl.export(context, 'run_control.context')
ctrl.export(xxx, 'xxx')


# SQLite needs to be used from only one thread.
# The _initialize(), _run(), _loop(), and _finalize() functions are called in one thread.
datastore = None



async def _initialize():
    global context, datastore
    datastore = sls.create_datastore_from_url('sqlite:///SlowTaskTest.db', 'test')

    load_context()
    context.running = False
    xxx['name'] = 'HELLO'
    

async def _finalize():
    datastore.close()
    

async def _loop():
    if context.running:
        for ch in range(4):
            x = float(device.ch(ch))
            datastore.append(x, tag='ch%02d'%ch)
            if ch == 0:
                a <= x
                await ctrl.publish(a, name='aa')
            if ch == 1:
                b <= x
                await ctrl.publish(b)
            if ch == 2:
                c <= x
                await ctrl.publish(c)
            if ch == 3:
                d <= x
                await ctrl.publish(d)
            
    await asyncio.sleep(0.5)


def start(run_number:int, stop_after:bool, run_length:float, repeat: bool, offline:bool):
    context.run_number = run_number
    context.stop_after = stop_after
    context.run_length = run_length
    context.repeat = repeat
    context.offline = offline
    context.running = True
    save_context()
    return True


def stop():
    context.running = False
    if not context.offline:
        context.run_number += 1
    save_context()
    return True



if __name__ == '__main__':
    async def main():
        await _initialize()
        ctrl.stop_by_signal()
        while not ctrl.is_stop_requested():
            await _loop()
        await _finalize()
    asyncio.run(main())
