import asyncio

from slowpy.mesh import Tasklet
tasklet = Tasklet()

from slowpy.control import control_system as ctrl
ctrl.import_control_module('AsyncRabbitMQ')
rabbitmq, command_queue_node, data_publish_node = None, None, None

x, step = 0, 1


@tasklet.initialize()
async def initialize(params):
    global rabbitmq, command_queue_node, data_publish_node
    rabbitmq = ctrl.async_rabbitmq('amqp://slowdash:slowdash@localhost')
    exchange = rabbitmq.topic_exchange('slowdash')
    
    command_queue_node = exchange.queue(name='command.randomwalk', exclusive=True)
    data_publish_node = exchange.publisher(routing_key='data.randomwalk')


@tasklet.finalize()
async def finalize():
    await rabbitmq.aio_close()

    
@tasklet.once()
async def run():
    await asyncio.gather(handle_commands(), start())

    
async def handle_commands():
    global x, step
    
    while not ctrl.is_stop_requested():
        message = await command_queue_node.aio_get()
        command = message.body
        if command is None:
            continue
        
        print(f'RandomwalkSystem: Received: {command}')
        if 'step' in command:
            step = command['step']
        if 'x' in command:
            x = command['x']


@tasklet.mesh.export()
async def start():
    global x, step
    
    import random
    while not ctrl.is_stop_requested():
        x = random.gauss(x, step)

        await data_publish_node.aio_set({'randomwalk':x})
        
        await ctrl.aio_sleep(1)


    
if __name__ == '__main__':
    tasklet.run()
