import time
from dataclasses import dataclass

@dataclass
class RunControl:
    auto_stop: bool = False
    run_length: float = 0
    start_time: float = 0
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
        if run_control.auto_stop:
            now = time.monotonic()
            if now - run_control.start_time >= run_control.run_length:
                run_control.running = False
                        
    ctrl.sleep(1)


def start(auto_stop:bool, run_length:float):
    run_control.auto_stop = auto_stop
    run_control.run_length = run_length

    run_control.start_time = time.monotonic()
    run_control.running = True
    
    
def stop():
    run_control.running = False
    
