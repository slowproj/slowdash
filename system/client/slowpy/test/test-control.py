#! /bin/env python3


import time

import slowpy as slp
ctrl = slp.ControlSystem()
ctrl.load_control_module('Dummy')

ch0 = ctrl.dummy_device().ch(0)
ch1 = ctrl.dummy_device().ch(1)

for i in range(10):
    print(ch0, ch1)
    time.sleep(1)

ch0.set(-10)

for i in range(10):
    print(ch0, ch1)
    time.sleep(1)
