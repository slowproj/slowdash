
print('MQTT Chat')
print('type ctrl-d to stop')


import asyncio

from slowpy.control import control_system as ctrl
mqtt = ctrl.import_control_module('AsyncMQTT').async_mqtt('localhost')


async def main():
    is_running = True

    async def reader():
        nonlocal is_running
        sub = mqtt.subscribe('chat/#', timeout=0.1)
        while is_running:
            message = await sub.aio_get()
            if message is not None:
                print(message.decode())

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
                await mqtt.publish('chat/all').aio_set(line)

    await asyncio.gather(reader(), writer())
    await mqtt.aio_close()


asyncio.run(main())
