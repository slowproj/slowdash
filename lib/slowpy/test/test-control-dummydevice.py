#! /bin/env python3

import time

from slowpy.control import ControlSystem
ControlSystem.import_control_module('DummyDevice')

dummy_device = ControlSystem().dummy_device()
ch0 = dummy_device.ch(0)
ch1 = dummy_device.ch(1)

for i in range(10):
    print(ch0, ch1)
    time.sleep(1)

ch0.set(-10)

for i in range(10):
    print(ch0, ch1)
    time.sleep(1)
