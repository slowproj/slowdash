#! /bin/env python3

import slowpy
ctrl = slowpy.ControlSystem()
ctrl.load_control_module('Dripline')
dripline = ctrl.dripline(dripline_config={'auth-file':'/project/authentications.json'})

peaches = dripline.endpoint('peaches')
print(peaches)
peaches.set(-10)
print(peaches)
