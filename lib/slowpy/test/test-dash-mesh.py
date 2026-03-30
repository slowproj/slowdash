
import asyncio
from slowpy.dash import Mesh


async def main(mesh_url):
    mesh = Mesh(mesh_url)
    
    is_running = True
    async def writer():
        print('type ctrl-d to stop')
        nonlocal is_running
        while is_running:
            try:
                line = await asyncio.to_thread(input)
                await mesh.aio_publish('chat.all', line, headers={'sender':'me'})
            except:
                is_running = False

    async def reader():
        sub = mesh.subscriber('chat.>')
        while is_running:
            headers, data = await sub.aio_get()
            if data is not None:
                print(f'{headers}: {data}')
        
    await asyncio.gather(writer(), reader())
    await mesh.aio_close()


if __name__ == '__main__':
    #mesh = None
    mesh = 'slowmq://localhost:18881'
    #mesh = 'nats://localhost'
    #mesh = 'mqtt://localhost'
    #mesh = 'redis://localhost/12'
    #mesh = 'amqp://slowdash:slowdash@localhost/SlowMesh'
    
    asyncio.run(main(mesh))
