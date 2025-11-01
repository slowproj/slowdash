
from slowpy.control import control_system as ctrl
ctrl.import_control_module('AsyncRabbitMQ')
rabbitmq, command_publish, data_queue = None, None, None


async def _initialize(params):
    global rabbitmq, data_queue, command_publish
    rabbitmq = ctrl.rabbitmq('amqp://slowdash:slowdash@localhost')
    exchange = rabbitmq.topic_exchange('slowdash')
    
    command_publish = exchange.publish(routing_key='command.randomwalk')
    data_queue = exchange.queue(name='control', routing_key='data.*', exclusive=True)


async def _finalize():
    await rabbitmq.aio_close()

    
async def _run():
    await command_publish.aio_set({'x':100, 'step':10})
    
    while not ctrl.is_stop_requested():
        message = await data_queue.aio_get()
        data = message.body
        if data is None:
            continue

        print(data)
        await ctrl.aio_publish(data['randomwalk'], name='randomwalk')
        

    
# make this script independently executable
if __name__ == '__main__':
    from slowpy.dash import Tasklet
    Tasklet().run()
