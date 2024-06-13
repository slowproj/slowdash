#! /bin/env python3

from slowpy.control import ControlSystem
ctrl = ControlSystem()

ctrl.load_control_module('Dripline')
dripline = ctrl.dripline(dripline_config={'auth-file':'/project/authentications.json'})

peaches = dripline.endpoint('peaches')
print(peaches)
peaches.set(-10)
print(peaches)
print(peaches.calibrated())
