#! /bin/env python3

from slowpy.control import ControlSystem
ControlSystem.import_control_module('Dripline')

dripline = ControlSystem().dripline(dripline_config={'auth-file':'/home/slowuser/authentications.json'})
peaches = dripline.endpoint('peaches')

print(peaches)
peaches.set(-10)
print(peaches)
print(peaches.calibrated())
