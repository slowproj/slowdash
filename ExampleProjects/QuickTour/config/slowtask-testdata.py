
import time, logging
from slowpy.control import DummyDevice_RandomWalk, ControlSystem
from slowpy.store import DataStore_SQLite


def _initialize(params):
    global device, datastore
    device = DummyDevice_RandomWalk(n=4)
    datastore = DataStore_SQLite('sqlite:///QuickTourTestData.db', table="testdata")

    
def _loop():
    for ch in range(4):
        data = device.read(ch)
        datastore.append(data, tag="ch%02d"%ch)
    time.sleep(1)


def _finalize():
    datastore.close()

    
if __name__ == '__main__':
    _initialize({})
    ControlSystem.stop_by_signal()
    while not ControlSystem.is_stop_requested():
        _loop()
