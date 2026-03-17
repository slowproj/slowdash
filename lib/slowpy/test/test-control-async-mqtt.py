
print('MQTT Chat')
print('type ctrl-d to stop')


import asyncio

from slowpy.control import control_system as ctrl
mqtt = ctrl.import_control_module('AsyncMQTT').async_mqtt('localhost')


async def aio_input(prompot=""):
    try:
        return await asyncio.to_thread(input, prompot)
    except:
        return None

            
async def main():
    is_running = True

    async def writer():
        pub = mqtt.publish('chat/all')
        nonlocal is_running
        while is_running:
            line = await aio_input()
            if line is None:
                is_running = False
            else:
                await pub.aio_set(line)

    async def reader():
        sub = mqtt.subscribe('chat/#', timeout=0.1)
        nonlocal is_running
        while is_running:
            message = await sub.payload().aio_get()
            if message is not None:
                print(message.decode())

    await asyncio.gather(writer(), reader())
    await mqtt.aio_close()


asyncio.run(main())
