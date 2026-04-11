
from slowpy.control import control_system as ctrl
ctrl.import_control_module('AsyncDripline')
dripline = ctrl.async_dripline('amqp://dripline:dripline@rabbit-broker')
print(f'hello from {__name__}')


async def _run():
    endpoint_stats = {}

    while not ctrl.is_stop_requested():
        # receive a data packet from Dripline Mesh
        message = await dripline.sensor_value_queue().aio_get()
        if message is None or message.body is None:
            continue
        endpoint_name = message.parameters['routing_key'].split('.')[1]
        timestamp = message.headers.get('timestamp', None)
        value_raw = message.body.get('value_raw', None)

        # analyze data
        n, sum = endpoint_stats.get(endpoint_name, (0, 0))
        n += 1
        sum += value_raw
        endpoint_stats[endpoint_name] = (n, sum)
    
        # push the analyzed data to SlowDash
        await ctrl.aio_publish(n, name=f'{endpoint_name}.n')
        await ctrl.aio_publish(sum/n, name=f'{endpoint_name}.mean')


async def _finalize():
    await dripline.aio_close()
    
