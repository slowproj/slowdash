
import time, json
from slowpy import Histogram
from slowpy.control import RandomWalkDevice
from slowpy.store import DataStore_SQLite, BlobStorage_File

datastore = DataStore_SQLite('sqlite:///SlowTestData.db', table="Test")
blob_storage = BlobStorage_File(names=['hist', '%Y-%m', '%y%m%d-%H%M%S-%Z'], ext='.json')

device = RandomWalkDevice(n=4)
histogram = Histogram(nbins=20, range_min=-10, range_max=10)

while True:
    histogram.fill(device.read(0))
    data = json.dumps(histogram.to_json()).encode()
    
    blob_id = blob_storage.write(data)
    datastore.append(blob_id, tag="hist_json")
    
    time.sleep(1)
