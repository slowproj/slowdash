
from slowpy.control import control_system as ctrl
ctrl.import_control_module('AsyncRabbitMQ')
rabbitmq, command_publish_node, data_queue_node = None, None, None

from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///SlowTestData', 'ts_data')


async def _initialize(params):
    global rabbitmq, data_queue_node, command_publish_node
    rabbitmq = ctrl.rabbitmq('amqp://slowdash:slowdash@localhost')
    exchange = rabbitmq.topic_exchange('slowdash')
    
    command_publish_node = exchange.publish(routing_key='command.randomwalk')
    data_queue_node = exchange.queue(name='control', routing_key='data.*', exclusive=True)


async def _finalize():
    await rabbitmq.aio_close()

    
async def _run():
    await command_publish_node.aio_set({'x':100, 'step':10})
    
    while not ctrl.is_stop_requested():
        message = await data_queue_node.aio_get()
        data = message.body
        if data is None:
            continue

        print(data)
        datastore.append(data)
        

    
# make this script independently executable
if __name__ == '__main__':
    from slowpy.dash import Tasklet
    Tasklet().run()
