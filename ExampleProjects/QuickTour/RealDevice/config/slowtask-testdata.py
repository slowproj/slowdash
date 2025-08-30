from slowpy.control import control_system as ctrl
device = ctrl.ethernet('172.26.0.1', 5025).scpi()

from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///QuickTourTestData.db', table="testdata")


device.command('*RST').set()


def _loop():
    volt = device.command('MEAS:VOLT:DC?').get()

    datastore.append({'volt': volt})
    ctrl.sleep(1)

    

if __name__ == '__main__':
    ctrl.stop_by_signal()
    while not ctrl.is_stop_requested():
        _loop()
    
