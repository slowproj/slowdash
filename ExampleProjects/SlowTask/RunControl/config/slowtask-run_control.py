import sys, os, time, json, logging
from dataclasses import dataclass, asdict
from slowpy.control import ControlSystem, ControlNode
import slowpy.store as sls

ControlSystem.import_control_module('DummyDevice')
device = ControlSystem().randomwalk_device()
ch0, ch1, ch2, ch3 = [ device.ch(ch) for ch in range(4) ]


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
    global context
    if os.path.isfile('run_context.json'):
        try:
            with open('run_context.json') as f:
                data = json.load(f)
                context = Context(**data)
        except Exception as e:
            print(e)


class DataclassNode(ControlNode):
    def get(self):
        return {
            'tree': {
                'run_number': context.run_number,
                'stop_after': context.stop_after,
                'run_length': context.run_length,
                'repeat': context.repeat,
                'offline': context.offline,
                'running': context.running,
            }
        }

def _export():
    return [
        ('context', DataclassNode()),
    ]



# SQLite needs to be used from only one thread.
# The _initialize(), _run(), _loop(), and _finalize() functions are called in one thread.
datastore = None



def _initialize():
    global context, datastore
    datastore = sls.create_datastore_from_url('sqlite:///SlowTaskTest.db', 'test')

    load_context()
    context.running = False
    

def _finalize():
    datastore.close()
    

def _loop():
    if context.running:
        for ch in range(4):
            x = float(device.ch(ch))
            datastore.append(x, tag='ch%02d'%ch)
            
    time.sleep(1)


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
    _initialize({})
    ControlSystem.stop_by_signal()
    while not ControlSystem.is_stop_requested():
        _loop()
    _finalize()
