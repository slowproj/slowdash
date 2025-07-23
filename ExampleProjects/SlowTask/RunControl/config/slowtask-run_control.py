import sys, os, time, json, logging
from dataclasses import dataclass, asdict
from slowpy.control import ControlSystem, ControlNode
import slowpy.store as sls

ControlSystem.import_control_module('DummyDevice')
device = ControlSystem().randomwalk_device()
ch0, ch1, ch2, ch3 = [ device.ch(ch) for ch in range(4) ]


@dataclass
class Context:
    run_number: int = 0
    is_running: bool = False
context = Context()



class DataclassNode(ControlNode):
    def get(self):
        return {
            'tree': {
                'run_number': context.run_number,
                'is_running': context.is_running,
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

    if os.path.isfile('run_context.json'):
        try:
            with open('run_context.json') as f:
                data = json.load(f)
                context = Context(**data)
        except:
            pass
    context.is_running = False
    

def _finalize():
    datastore.close()
    with open('run_context.json', 'w') as f:
        json.dump(asdict(context), f)
    

def _loop():
    if context.is_running:
        for ch in range(4):
            x = float(device.ch(ch))
            datastore.append(x, tag='ch%02d'%ch)
            
    time.sleep(1)


def start():
    context.run_number += 1
    context.is_running = True
    return True


def stop():
    context.is_running = False
    return True



if __name__ == '__main__':
    _initialize({})
    ControlSystem.stop_by_signal()
    while not ControlSystem.is_stop_requested():
        _loop()
    _finalize()
