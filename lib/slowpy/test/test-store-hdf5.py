
import time
from slowpy import Histogram
from slowpy.control import RandomWalkDevice
from slowpy.store import DataStore_HDF5

datastore = DataStore_HDF5('hdf5:///TestData.h5', dataset='test')
device = RandomWalkDevice(n=4)


def _loop():
    records = { 'ch%01d'%ch: device.read(ch) for ch in range(4) }
    print(records)
    
    datastore.append(records)
    time.sleep(1)

    
if __name__ == '__main__':
    from slowpy.dash import Tasklet
    slowtask = Tasklet()
    slowtask.run()
    
