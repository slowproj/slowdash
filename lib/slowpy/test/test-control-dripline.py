#! /bin/env python3

from slowpy.control import ControlSystem
dripline = ControlSystem.import_control_module('Dripline').dripline(
    dripline_config={'auth-file':'/project/authentications.json'}
)
peaches = dripline.endpoint('peaches')

print(peaches)
peaches.set(-10)
print(peaches)
print(peaches.calibrated())
