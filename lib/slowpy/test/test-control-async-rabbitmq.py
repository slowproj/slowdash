
print('RabbitMQ Chat')
print('type ctrl-d to stop')


import asyncio

from slowpy.control import control_system as ctrl
rabbitmq = ctrl.import_control_module('AsyncRabbitMQ').async_rabbitmq('amqp://slowdash:slowdash@localhost')
exchange = rabbitmq.topic_exchange('slowchat')


async def aio_input(prompot=""):
    try:
        return await asyncio.to_thread(input, prompot)
    except:
        return None
    
            
async def main():
    is_running = True

    async def writer():
        pub = exchange.publish(routing_key='chat.all')
        nonlocal is_running
        while is_running:
            line = await aio_input()
            if line is None:
                is_running = False
            else:
                await pub.json().aio_set({'input': line})

    async def reader():
        sub = exchange.queue(routing_key='chat.*', exclusive=True, timeout=0.1)
        nonlocal is_running
        while is_running:
            headers, data = await sub.json().aio_get()
            if data is not None:
                print(f'{headers}: {data}')

    await asyncio.gather(writer(), reader())
    await rabbitmq.aio_close()


asyncio.run(main())
