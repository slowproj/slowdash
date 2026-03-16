
print('Redis Chat')
print('type ctrl-d to stop')


import asyncio

from slowpy.control import control_system as ctrl
redis = ctrl.import_control_module('AsyncRedis').async_redis('redis://localhost:6379/12')


async def main():
    is_running = True

    async def reader():
        nonlocal is_running
        sub = redis.subscribe('chat:*')
        while is_running:
            message = await sub.data().aio_get()
            if message is not None:
                print(message)

    async def writer():
        nonlocal is_running
        async def ainput(prompot=""):
            try:
                return await asyncio.to_thread(input, prompot)
            except:
                return None
    
        while is_running:
            line = await ainput()
            if line is None:
                is_running = False
            else:
                await redis.publish('chat:all').aio_set(line)

    await asyncio.gather(reader(), writer())
    await redis.aio_close()


asyncio.run(main())
