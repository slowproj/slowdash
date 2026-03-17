
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

    async def reader():
        nonlocal is_running
        queue_node = exchange.queue(routing_key='chat.*', exclusive=True)    # using an exclusive queue
        #queue_node = exchange.queue('chat_receiver', routing_key='chat.*')  # using a shared queue
        while is_running:
            message = await queue_node.aio_get()
            data = message.body
            if data is None:
                continue
            print(data)

    async def writer():
        nonlocal is_running
        publish_node = exchange.publish(routing_key='chat.all')
        while is_running:
            line = await aio_input()
            if line is None:
                is_running = False
            else:
                await publish_node.aio_set(line)

    await asyncio.gather(reader(), writer())
    await rabbitmq.aio_close()


asyncio.run(main())
