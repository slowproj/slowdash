
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

print('hello from control_peaches.py')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')
peaches = dripline.endpoint('peaches').value_raw()


def set_peaches(target:float, ramping_rate:float):
    print(f'setting peaches to {target}, with ramping at {ramping_rate}')
    peaches.ramping(ramping_rate).set(target)
    
def abort_ramping():
    peaches.ramping().status().set(0)
    

ctrl.export(peaches.ramping(), name='ramping_target')
ctrl.export(peaches.ramping().status(), name='ramping_status')
