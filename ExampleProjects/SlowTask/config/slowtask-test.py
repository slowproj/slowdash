import time, logging
from slowpy.control import ControlSystem, ControlNode
import slowpy.store as sls

ControlSystem.import_control_module('DummyDevice')
device = ControlSystem().randomwalk_device()
print("Random-Walk Device Loaded")

#name = input('who are you?')
#print('hello, ' + name)



### Accepting Controls ###

def set_V0(V0, **kwargs):
    ramping = kwargs.get('ramping', 10)
    device.ch(0).ramping(ramping).set(V0)

def set_V1(V1, **kwargs):
    ramping = kwargs.get('ramping', 10)
    device.ch(1).ramping(ramping).set(V1)

def set_V2(V2, **kwargs):
    ramping = kwargs.get('ramping', 10)
    device.ch(2).ramping(ramping).set(V2)

def set_V3(V3, **kwargs):
    ramping = kwargs.get('ramping', 10)
    device.ch(3).ramping(ramping).set(V3)

def set_all(**kwargs):
    set_V0(**kwargs)
    set_V1(**kwargs)
    set_V2(**kwargs)
    set_V3(**kwargs)

def stop(**kwargs):
    device.ch(0).ramping().status().set(0)
    device.ch(1).ramping().status().set(0)
    device.ch(2).ramping().status().set(0)
    device.ch(3).ramping().status().set(0)


    
### Exporting Variables ###
    
class StatusNode(ControlNode):
    def get(self):
        return {
            'columns': [ 'Channel', 'Value', 'Ramping' ],
            'table': [
                [ 'Ch0', float(device.ch(0)), 'Yes' if device.ch(0).ramping().status().get() else 'No' ],
                [ 'Ch1', float(device.ch(1)), 'Yes' if device.ch(1).ramping().status().get() else 'No' ],
                [ 'Ch2', float(device.ch(2)), 'Yes' if device.ch(2).ramping().status().get() else 'No' ],
                [ 'Ch3', float(device.ch(3)), 'Yes' if device.ch(3).ramping().status().get() else 'No' ],
            ]
        }
    
def _export():
    return [
        ('V0', device.ch(0)),
        ('V1', device.ch(1)),
        ('V2', device.ch(2)),
        ('V3', device.ch(3)),
        ('Status', StatusNode())
    ]



### Storing Data ###

# SQLite needs to be used from only one thread.
# The _initialize(), _run(), _loop(), and _finalize() functions are called in one thread.

datastore = None

def _initialize(params):
    global datastore
    datastore = sls.create_datastore_from_url('sqlite:///SlowTaskTest.db', 'test')


def _finalize():
    global datastore
    del datastore


def _loop():
    for ch in range(4):
        value = float(device.ch(ch))
        datastore.append(value, tag='ch%02d'%ch)
    time.sleep(1)


    
### Stand-alone Testing ###
    
if __name__ == '__main__':
    _initialize({})
    ControlSystem.stop_by_signal()
    while not ControlSystem.is_stop_requested():
        _loop()
    _finalize()
