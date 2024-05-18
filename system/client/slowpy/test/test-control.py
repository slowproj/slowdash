#! /bin/env python3

import time

import slowpy as slp
ctrl = slp.ControlSystem()

ep_id = ctrl.ethernet('192.168.1.43', 12345).scpi('*idn')
print(ep_id)

V0 = ctrl.ethernet('192.168.1.43', 12345).scpi('MEAS:V0')
for i in range(10):
    print(float(V0)*2.3)
    time.sleep(1)

V0.set(-10)
for i in range(10):
    print(float(V0)*2.3)
    time.sleep(1)
