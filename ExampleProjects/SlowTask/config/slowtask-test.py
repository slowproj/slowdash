import time, logging
from slowpy.control import ControlSystem, ControlNode
import slowpy.store as sls

ControlSystem.import_control_module('DummyDevice')
device = ControlSystem().randomwalk_device()
ch0, ch1, ch2, ch3 = [ device.ch(ch) for ch in range(4) ]
print("Random-Walk Device Loaded")



#name = input('who are you?')
#print('hello, ' + name)



### Accepting Controls ###

def set_V0(V0:float, ramping:float=10):
    ch0.ramping(ramping).set(V0)

def set_V1(V1:float, ramping:float=10):
    ch1.ramping(ramping).set(V1)

def set_V2(V2:float, ramping:float=10):
    ch2.ramping(ramping).set(V2)

def set_V3(V3:float, ramping:float=10):
    ch3.ramping(ramping).set(V3)

def set_all(V0:float, V1:float, V2:float, V3:float, ramping:float):
    set_V0(V0, ramping)
    set_V1(V1, ramping)
    set_V2(V2, ramping)
    set_V3(V3, ramping)

def stop():
    ch0.ramping().status().set(0)
    ch1.ramping().status().set(0)
    ch2.ramping().status().set(0)
    ch3.ramping().status().set(0)


    
### Exporting Variables ###
    
class StatusNode(ControlNode):
    def get(self):
        return {
            'columns': [ 'Channel', 'Value', 'Ramping' ],
            'table': [
                [ 'Ch0', ch0.get(), 'Yes' if ch0.ramping().status().get() else 'No' ],
                [ 'Ch1', ch1.get(), 'Yes' if ch1.ramping().status().get() else 'No' ],
                [ 'Ch2', ch2.get(), 'Yes' if ch2.ramping().status().get() else 'No' ],
                [ 'Ch3', ch3.get(), 'Yes' if ch3.ramping().status().get() else 'No' ],
            ]
        }
    
def _export():
    return [
        ('V0', ch0),
        ('V1', ch1),
        ('V2', ch2),
        ('V3', ch3),
        ('Status', StatusNode())
    ]



### Storing Data ###

# SQLite needs to be used from only one thread.
# The _initialize(), _run(), _loop(), and _finalize() functions are called in one thread.

datastore = None

def _initialize(params):
    global datastore
    datastore = sls.create_datastore_from_url('sqlite:///SlowTaskTest.db', 'test')
    print("Hello from Random-Walk Device")


def _finalize():
    datastore.close()
    print("Bye-bye from Random-Walk Device")
    

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
