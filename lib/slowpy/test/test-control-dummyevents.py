
import time

from slowpy.control import control_system as ctrl
device = ctrl.import_control_module('DummyDevice').randomevent_device()

for i in range(10):
    t = time.time()
    ev = device.get()
    print(t, ev)
