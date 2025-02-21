#! /usr/bin/env python3        

import time
from slowpy import Histogram
from slowpy.control import RandomWalkDevice
from slowpy.store import DataStore_CSV

datastore = DataStore_CSV('csv:///SlowTestData.d', 'Test')
datastore_obj = datastore.another(table='Test2')
device = RandomWalkDevice(n=4)
histogram = Histogram(nbins=20, range_min=-10, range_max=10)


while True:
    records = { 'ch%01d'%ch: device.read(ch) for ch in range(4) }
    print(records)
    
    datastore.append(records)
    
    histogram.fill(records['ch0'])
    datastore_obj.append(histogram, tag="ch0_hist")
    
    time.sleep(1)
