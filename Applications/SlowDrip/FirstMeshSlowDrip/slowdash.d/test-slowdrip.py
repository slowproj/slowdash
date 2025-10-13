
import logging

from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')


def _initialize(params):
    rmq_url = params.get('rabbitmq_url', 'amqp://dripline:dripline@localhost')
    name = params.get('name', 'slowdrip2')
    
    global dripline
    dripline = ctrl.dripline(rmq_url, name)


def _run():
    peaches = dripline.endpoint('peaches')
    chips = dripline.endpoint('chips')
    peaches.set(1111)
    print(chips.get())

    while not ctrl.is_stop_requested():
        value, *_ = dripline.sensor_value_queue().get()
        #value = await dripline.heartbeat_queue().get()
        #value, *_ = await dripline.status_message_queue().get()
        print(f'QUEUE: {value}')
    
    
        
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    from slowpy.dash import Tasklet
    task = Tasklet()
    task.run()
