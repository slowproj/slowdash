
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')
dripline = ctrl.dripline('amqp://dripline:dripline@localhost')


peaches = dripline.endpoint('peaches')
chips = dripline.endpoint('chips')
peaches.set(1234)

ctrl.stop_by_signal()
while not ctrl.is_stop_requested():
    print(peaches.value_cal().get())
    print(chips.value_raw().get())
    ctrl.sleep(1)
