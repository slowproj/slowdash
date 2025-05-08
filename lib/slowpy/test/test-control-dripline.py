
from slowpy.control import control_system as ctrl
dripline = ctrl.import_control_module('Dripline').dripline(dripline_config={'auth-file':'/home/slowuser/authentications.json'})

peaches = dripline.endpoint('peaches')

print(peaches)
peaches.set(-10)
print(peaches)
print(peaches.calibrated())
