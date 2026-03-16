
print('RabbitMQ Chat')
print('type ctrl-d to stop')


import asyncio

from slowpy.control import control_system as ctrl
rabbitmq = ctrl.import_control_module('AsyncRabbitMQ').async_rabbitmq('amqp://slowdash:slowdash@localhost')
exchange = rabbitmq.topic_exchange('slowchat')


async def main():
    is_running = True

    async def reader():
        nonlocal is_running
        queue_node = exchange.queue(routing_key='chat.*', exclusive=True)
        while is_running:
            message = await queue_node.aio_get()
            data = message.body
            if data is None:
                continue
            print(data)

    async def writer():
        nonlocal is_running
        async def ainput(prompot=""):
            try:
                return await asyncio.to_thread(input, prompot)
            except:
                return None
    
        publish_node = exchange.publish(routing_key='chat.all')
        while is_running:
            line = await ainput()
            if line is None:
                is_running = False
            else:
                await publish_node.aio_set(line)

    await asyncio.gather(reader(), writer())
    await rabbitmq.aio_close()


asyncio.run(main())
