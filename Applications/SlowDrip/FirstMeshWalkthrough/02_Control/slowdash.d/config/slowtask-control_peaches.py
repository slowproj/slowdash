
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

dripline, peaches = None, None


def _initialize(params):
    global dripline, peaches
    rmq_url = params.get('RMQ_URL', 'amqp://dripline:dripline@localhost')
    dripline = ctrl.dripline(rmq_url)
    peaches = dripline.endpoint('peaches')
    print('hello from peaches')
    

def set_peaches(value:float):
    print(f'setting peaches to {value}')
    peaches.set(value)
