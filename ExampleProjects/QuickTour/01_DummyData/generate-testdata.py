#! /usr/bin/python3

import slowpy.control
import slowpy.store


class TestDataFormat(slowpy.store.LongTableFormat):
    schema_numeric = '(datetime DATETIME, timestamp INTEGER, channel VARCHAR(100), value REAL, PRIMARY KEY(timestamp, channel))'
    def insert_numeric_data(self, cur, timestamp, channel, value):
        cur.execute(f'INSERT INTO {self.table} VALUES(CURRENT_TIMESTAMP,{int(timestamp)},?,{float(value)})', (str(channel),))


ctrl = slowpy.control.ControlSystem()
device = slowpy.control.RandomWalkDevice(n=4)
datastore = slowpy.store.DataStore_SQLite('sqlite:///QuickTourTestData.db', table="testdata", table_format=TestDataFormat())


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
