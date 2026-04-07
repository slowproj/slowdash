from dataclasses import dataclass

@dataclass
class RunControl:
    running: bool = False
run_control = RunControl
    

from slowpy.control import control_system as ctrl
device = ctrl.ethernet('192.168.50.121', 5025).scpi()

from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///QuickTourTestData.db', table="testdata")


def _loop():
    if run_control.running:
        volt = device.command('MEAS:VOLT:DC?').get()
        datastore.append({'volt': float(volt)})
        
    ctrl.sleep(1)


def start():
    run_control.running = True
    
    
def stop():
    run_control.running = False
    
