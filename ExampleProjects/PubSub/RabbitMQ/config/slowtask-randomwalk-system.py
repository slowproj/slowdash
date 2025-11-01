
from slowpy.control import control_system as ctrl
ctrl.import_control_module('AsyncRabbitMQ')
rabbitmq, command_queue, data_publish = None, None, None

x, step = 0, 1


async def _initialize(params):
    global rabbitmq, command_queue, data_publish
    rabbitmq = ctrl.rabbitmq('amqp://slowdash:slowdash@localhost')
    exchange = rabbitmq.topic_exchange('slowdash')
    
    command_queue = exchange.queue(name='command.randomwalk', exclusive=True)
    data_publish = exchange.publish(routing_key='data.randomwalk')


async def _finalize():
    await rabbitmq.aio_close()

    
async def _run():
    import asyncio
    await asyncio.gather(handle_commands(), start())

    
async def handle_commands():
    global x, step
    
    while not ctrl.is_stop_requested():
        message = await command_queue.aio_get()
        command = message.body
        if command is None:
            continue
        
        print(f'RandomwalkSystem: Received: {command}')
        if 'step' in command:
            step = command['step']
        if 'x' in command:
            x = command['x']


async def start():
    global x, step
    
    import random
    while not ctrl.is_stop_requested():
        x = random.gauss(x, step)

        await data_publish.aio_set({'randomwalk':x})
        
        await ctrl.aio_sleep(1)


    
# make this script independently executable
if __name__ == '__main__':
    from slowpy.dash import Tasklet
    Tasklet().run()
