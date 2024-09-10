#! /bin/env python3

import time
from slowpy.control import ControlSystem
ControlSystem.import_control_module('LabJack')
u12 = ControlSystem().labjack_U12()

aout0 = u12.aout(0)
ain0 = u12.ain(0)
dout0 = u12.dout(0)
din1 = u12.din(1)

aout0.set(0)
for i in range(10):
    aout0.set(i/2.0)
    dout0.set((i%4)<2)
    print(ain0, din1)
    time.sleep(1)

aout0.set(0)
dout0.set(0)
