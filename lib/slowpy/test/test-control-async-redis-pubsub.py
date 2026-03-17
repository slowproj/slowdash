
print('Redis Chat')
print('type ctrl-d to stop')


import asyncio

from slowpy.control import control_system as ctrl
redis = ctrl.import_control_module('AsyncRedis').async_redis('redis://localhost:6379/12')


async def aio_input(prompot=""):
    try:
        return await asyncio.to_thread(input, prompot)
    except:
        return None
    
    
async def main():
    is_running = True

    async def writer():
        pub = redis.publish('chat:all')
        nonlocal is_running
        while is_running:
            line = await aio_input()
            if line is None:
                is_running = False
            else:
                await pub.aio_set(line)

    async def reader():
        sub = redis.subscribe('chat:*')
        nonlocal is_running
        while is_running:
            message = await sub.data().aio_get()
            if message is not None:
                print(message)

    await asyncio.gather(writer(), reader())
    await redis.aio_close()


asyncio.run(main())
