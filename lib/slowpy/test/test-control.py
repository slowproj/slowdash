#! /bin/env python3


import time
from slowpy.control import ControlSystem

ctrl = ControlSystem()
ctrl.load_control_module('DummyDevice')

ch0 = ctrl.dummy_device().ch(0)
ch1 = ctrl.dummy_device().ch(1)

for i in range(10):
    print(ch0, ch1)
    time.sleep(1)

ch0.set(-10)

for i in range(10):
    print(ch0, ch1)
    time.sleep(1)
