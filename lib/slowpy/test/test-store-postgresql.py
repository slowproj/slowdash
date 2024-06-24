#! /usr/bin/env python3        

import time
from slowpy import Histogram
from slowpy.control import DummyDevice_RandomWalk
from slowpy.store import DataStore_PostgreSQL

db_url = 'postgresql://postgres:postgres@localhost:5432/SlowTestData'
datastore = DataStore_PostgreSQL(db_url, table_name="Test")
json_datastore = DataStore_PostgreSQL(db_url, table_name="Test2")
device = DummyDevice_RandomWalk(n=4)
histogram = Histogram(nbins=20, range_min=-10, range_max=10)


while True:
    records = { 'ch%01d'%ch: device.read(ch) for ch in range(4) }
    print(records)
    
    datastore.append(records)
    
    histogram.fill(records['ch0'])
    json_datastore.update(histogram, tag="ch0_hist")
    
    time.sleep(1)
