
import time, datetime, threading

from slowpy.control import control_system as ctrl
device = ctrl.import_control_module('DummyDevice').randomwalk_device()
device.is_running = False

from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///TestData2.db', table='slowdata')


def _initialize():
#    print("Initialized")
    device.ch(1).set(-5)

    
def _loop():
    if device.is_running:
        data = device.ch(1).get()
        
        print(f'STORE: {data}')
        datastore.append(data, tag='HV.ch1.V')
        
        tasklet.mesh.publish('data.stream.HV.ch1.V', {'HV.ch1.V':{'t': time.time(), 'x': data}})

    time.sleep(1)


def set_value(value:float=0):
    print(f'set: {value}')
    device.ch(0).set(value)

    
def start(**params):
    print(f'start: {params}')
    device.is_running = True

@@
def stop(**params):
    print(f'stop: {params}')
    device.is_running = False



if __name__ == '__main__':
    _initialize()
    
    t = threading.Thread(target=start, args=({},))
    t.start()

    time.sleep(10)
    
    stop({})
    t.join()
