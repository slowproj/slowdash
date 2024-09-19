
from slowpy.control import ControlSystem, RandomWalkDevice
from slowpy.store import DataStore_SQLite, LongTableFormat


class TestDataFormat(LongTableFormat):
    schema_numeric = '(datetime DATETIME, timestamp INTEGER, channel STRING, value REAL, PRIMARY KEY(timestamp, channel))'
    def insert_numeric_data(self, cur, timestamp, channel, value):
        cur.execute(f'INSERT INTO {self.table} VALUES(CURRENT_TIMESTAMP,%d,?,%f)' % (timestamp, value), (channel,))

        
ctrl = ControlSystem()
device = RandomWalkDevice(n=4)
datastore = DataStore_SQLite('sqlite:///QuickTourTestData.db', table="testdata", table_format=TestDataFormat())


def _loop():
    for ch in range(4):
        data = device.read(ch)
        datastore.append(data, tag="ch%02d"%ch)
    ctrl.sleep(1)

    
def _finalize():
    datastore.close()

    
    
if __name__ == '__main__':
    ctrl.stop_by_signal()
    while not ctrl.is_stop_requested():
        _loop()
    _finalize()
