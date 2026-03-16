import time

from slowpy.control import control_system as ctrl
redis = ctrl.import_control_module('AsyncRedis').async_redis('redis://localhost:6379/12')


async def main():
    # string
    await redis.string('name').aio_set('SlowDash')
    print(await redis.string('name').aio_get())
    
    # hash
    await redis.hash("Status").field("Count").aio_set(10)
    print(await redis.hash("Status").aio_get())
    print(await redis.hash("Status").field("Count").aio_get())
    
    # time-series
    await redis.ts('ch00').current().aio_set(123)
    await redis.ts('ch00').aio_set([(int(1000*(time.time()-100)), 456)])
    print(await redis.ts('ch00').aio_get())
    print(await redis.ts('ch00').last().time().aio_get())
    print(await redis.ts('ch00').last().lapse().aio_get())
    
    # JSON
    j = redis.json("jj")
    await j.aio_set({'foo': 'FOO', 'bar': {'buz': 'BUZ', 'qux': 'QUX'}})
    print(await j.aio_get())
    await j.node('bar').node('foo').aio_set(1)
    print(await j.node('bar').aio_get())


import asyncio
asyncio.run(main())

