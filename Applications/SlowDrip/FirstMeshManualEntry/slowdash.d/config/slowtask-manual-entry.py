
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

print('hello from manual-entry.py')
#dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')
dripline = ctrl.dripline('amqp://dripline:dripline@localhost')


def write_value(name:str, value:float):
    print(f'writing {name}={value} ')
    dripline.sensor_value_alert(name=name).set(value)
