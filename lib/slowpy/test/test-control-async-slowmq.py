import asyncio

from slowpy.control import control_system as ctrl
slowmq = ctrl.import_control_module('AsyncSlowMQ').async_slowmq('slowmq://localhost:18881')


async def aio_input(prompot=""):
    try:
        return await asyncio.to_thread(input, prompot)
    except:
        return None
    

async def main():
    is_running = True
    print('type ctrl-d to stop')

    async def writer():
        pub = slowmq.publisher('chat.all')
        nonlocal is_running
        while is_running:
            line = await aio_input()
            if line is None:
                is_running = False
            else:
                await pub.json().aio_set(line)

    async def reader():
        sub = slowmq.subscriber('chat.*', timeout=0.1)
        nonlocal is_running
        while is_running:
            headers, data = await sub.json().aio_get()
            if data is not None:
                print(f'{headers}: {data}')

    await asyncio.gather(writer(), reader())
    await slowmq.aio_close()


asyncio.run(main())
