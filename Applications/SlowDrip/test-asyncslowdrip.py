
import asyncio, logging

from slowpy.control import control_system as ctrl
ctrl.import_control_module('AsyncDripline')


async def _initialize(params):
    rmq_url = params.get('rabbitmq_url', 'amqp://dripline:dripline@localhost')
    name = params.get('name', 'slowdrip')
    
    global dripline
    dripline = ctrl.dripline(rmq_url, name)


async def _run():
    await asyncio.gather(run_queue(), run_alert(), run_service(), do())
    

async def do():
    peaches = dripline.endpoint('peaches')
    await peaches.aio_set(30000)
    
    slowdrip = dripline.endpoint('slowdrip')
    while not ctrl.is_stop_requested():
        await ctrl.aio_sleep(2)
        req = 'hello'
        rep = await slowdrip.aio_set(req)
        print(f'SET: {req} ---> {rep}')

    
async def run_queue():
    while not ctrl.is_stop_requested():
        value, *_ = await dripline.sensor_value_queue().aio_get()
        #value = await dripline.heartbeat_queue().aio_get()
        #value, *_ = await dripline.status_message_queue().aio_get()
        print(f'QUEUE: {value}')

        
async def run_alert():
    while not ctrl.is_stop_requested():
        await dripline.sensor_value_alert().aio_set((12345, 54321))
        await dripline.heartbeat_alert().aio_set(12345)
        await ctrl.aio_sleep(10)
    

async def run_service():
    async def handler(msg):
        operation = msg.headers.get('message_operation', -1)
        print(f'REQUEST: op={operation}, body={msg.body}')
        return {'status': 'handled', 'request': msg.body}
    while not ctrl.is_stop_requested():
        await dripline.request(handler).aio_get()
    
        
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    from slowpy.dash import Tasklet
    task = Tasklet()
    task.run()
