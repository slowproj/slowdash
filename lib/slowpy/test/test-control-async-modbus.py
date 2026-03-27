
#host, port = '192.168.50.63', 502
host, port = 'localhost', 1502

import asyncio

from slowpy.control import control_system as ctrl
modbus = ctrl.import_control_module('AsyncModbus').async_modbus(host, port)


async def main():
    reg0 = modbus.register32(0x10)
    reg1 = modbus.register32(0x11)

    await reg0.aio_set(0x12345678)
    await reg1.aio_set(0xabcdef00)

    while True:
        try:
            await reg0.aio_set((await reg0.aio_get()) + 1)
            await reg1.aio_set((await reg1.aio_get()) + 1)

            print(hex(await reg0.aio_get()))
            print(hex(await reg1.aio_get()))
        except Exception as e:
            pass
        
        await asyncio.sleep(1)


if __name__ == '__main__':
    asyncio.run(main())
