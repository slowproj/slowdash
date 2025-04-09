

import aio_pika, json

from slowpy.control import ControlSystem, ControlNode

sensor_values = {}


class SensorsNode(ControlNode):
    def get(self):
        t = {
            'columns': [ 'Name', 'Time', 'ValueRaw', 'ValueCal' ],
            'table': [
                [ name, entry.get('timestamp', ''), entry.get('value_raw', ''), entry.get('value_cal', '') ]
                for name, entry in sensor_values.items()
            ]
        }
        print(t)
        return t


def _export():
    return [
        ('CurrentSensorValues', SensorsNode()),
    ]



def on_message(message):
    name = message.routing_key
    if name.startswith('sensor_value.'):
        name = name[13:]
    else:
        return
    
    global sensor_values
    record = {
        'timestamp': message.headers.get("timestamp", None),
    }
    record.update(json.loads(message.body.decode()))
    sensor_values[name] = record
    print(f'"{name}": {record}')

    
        
async def _run():
    connection = await aio_pika.connect_robust('amqp://dripline:dripline@localhost')
    async with connection:
        channel = await connection.channel()
        alerts_exchange = await channel.declare_exchange('alerts', aio_pika.ExchangeType.TOPIC)
        requests_exchange = await channel.declare_exchange('requests', aio_pika.ExchangeType.TOPIC)
        queue = await channel.declare_queue(name='slowdash', exclusive=True)
        await queue.bind(alerts_exchange, routing_key='sensor_value.*')
        await queue.bind(alerts_exchange, routing_key='heartbeat.*')

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    on_message(message)



if __name__ == '__main__':                    
    import asyncio
    asyncio.run(_run())
