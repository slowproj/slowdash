#! /bin/env python3


#host, port = '10.19.72.198', 10000
host, port = '192.168.1.43', 17674


import time
import signal
from slowpy.control import ControlSystem

ctrl = ControlSystem()
ctrl.stop_by_signal()

ep_id = ctrl.ethernet(host, port).scpi('*idn')
print("ID: %s" % str(ep_id))

V0 = ctrl.ethernet(host, port).scpi('MEAS:V0')

while not ctrl.is_stop_requested():
    V0.ramp(1).set(10)
    for i in range(10):
        print(float(V0)*2.3)
        if not ctrl.sleep(1):
            break

    V0.ramp(1).set(-10)
    for i in range(10):
        print(float(V0)*2.3)
        if not ctrl.sleep(1):
            break

print("bye")
