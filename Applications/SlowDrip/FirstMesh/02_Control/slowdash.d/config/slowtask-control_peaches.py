
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

print('hello from control_peaches.py')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')
peaches = dripline.endpoint('peaches')


def set_peaches(value:float):
    print(f'setting peaches to {value}')
    peaches.set(value)
