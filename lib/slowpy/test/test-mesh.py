import asyncio
from slowpy.dash import Mesh

mesh = Mesh('slowmq://localhost:18881')
#mesh = Mesh('nats://localhost')
#mesh = Mesh('mqtt://localhost')
#mesh = Mesh('redis://localhost/12')
#mesh = Mesh('amqp://slowdash:slowdash@localhost/SlowMesh')


async def aio_input(prompot=""):
    try:
        return await asyncio.to_thread(input, prompot)
    except:
        return None
    

@mesh.on('chat.*')
async def handle(headers, data):
    print(f'{headers}: {data}')

    
async def main():
    print('type ctrl-d to stop')

    task = asyncio.create_task(mesh.aio_start())
    
    while True:
        line = await aio_input()
        if line is None:
            break
        else:
            await mesh.aio_publish('chat.all', line)

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    await mesh.aio_close()
    
asyncio.run(main())
