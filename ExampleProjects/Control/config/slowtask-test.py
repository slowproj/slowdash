
import time, logging
import slowpy as slp

ctrl = slp.ControlSystem()
ctrl.load_control_module('DummyDevice')
device = ctrl.dummy_device()


def set(**kwargs):
    ramping = kwargs.get('ramping', 10)
    for key, value in kwargs.items():
        if key == 'V0':
            device.ch(0).ramp(ramping).set(value)
        elif key == 'V1':
            device.ch(1).ramp(ramping).set(value)
        elif key == 'V2':
            device.ch(2).ramp(ramping).set(value)
        elif key == 'V3':
            device.ch(3).ramp(ramping).set(value)

def set_V0(V0, **kwargs):
    ramping = kwargs.get('ramping', 10)
    device.ch(0).ramp(ramping).set(V0)

def set_V1(V1, **kwargs):
    ramping = kwargs.get('ramping', 10)
    device.ch(1).ramp(ramping).set(V1)

def set_V2(V2, **kwargs):
    ramping = kwargs.get('ramping', 10)
    device.ch(0).ramp(ramping).set(V2)
    device.ch(2).set(V2)

def set_V3(V3, **kwargs):
    ramping = kwargs.get('ramping', 10)
    device.ch(3).ramp(ramping).set(V3)


class StatusNode(slp.ControlNode):
    def get(self):
        return {
            "Current Values": {
                'V0': float(device.ch(0)),
                'V1': float(device.ch(1)),
                'V2': float(device.ch(2)),
                'V3': float(device.ch(3))
            },
            "Ramping": {
                'V0': device.ch(0).ramp().get(),
                'V1': device.ch(1).ramp().get(),
                'V2': device.ch(2).ramp().get(),
                'V3': device.ch(3).ramp().get()
            }
        }
    
def export():
    return [
        ('V0', device.ch(0)),
        ('V1', device.ch(1)),
        ('V2', device.ch(2)),
        ('V3', device.ch(3)),
        ('Status', StatusNode())
    ]


datastore = None

def initialize(params):
    global datastore
    datastore = slp.create_datastore_from_url('sqlite:///SlowTaskTest.db', 'test')

def finalize():
    global datastore
    del datastore
    
def loop():
    for ch in range(4):
        value = float(device.ch(ch))
        datastore.write_timeseries(value, tag='ch%02d'%ch)
        
    time.sleep(1)

    
    
if __name__ == '__main__':
    initialize({})
    while True:
        for ch in range(4):
            print(device.ch(ch))
        loop()
