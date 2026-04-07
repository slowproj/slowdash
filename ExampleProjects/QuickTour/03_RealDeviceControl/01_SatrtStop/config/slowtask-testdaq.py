from dataclasses import dataclass

@dataclass
class RunStatus:
    running: bool = False
run_status = RunStatus()
    

from slowpy.control import control_system as ctrl
device = ctrl.ethernet('192.168.1.34', 5025).scpi()

from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///QuickTourTestData.db', table="testdata")


def _loop():
    if run_status.running:
        volt = device.command('MEAS:VOLT:DC?').get()
        datastore.append({'volt': float(volt)})
        
    ctrl.sleep(1)


def start():
    run_status.running = True
    
    
def stop():
    run_status.running = False
    
