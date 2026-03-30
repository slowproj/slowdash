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
    print('type ctrl-d to stop')

    async def writer():
        pub = redis.publisher('chat:all')
        nonlocal is_running
        while is_running:
            line = await aio_input()
            if line is None:
                is_running = False
            else:
                await pub.json({'sender':'me'}).aio_set({'message':line})

    async def reader():
        sub = redis.subscriber('chat:*', timeout=0.1)
        nonlocal is_running
        while is_running:
            headers, data = await sub.json().aio_get()
            if data is not None:
                print(f'{headers}: {data}')

    await asyncio.gather(writer(), reader())
    await redis.aio_close()


asyncio.run(main())
