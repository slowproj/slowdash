import asyncio
from slowpy.dash import Mesh

mesh = Mesh()
#mesh = Mesh('slowmq://localhost:18881')
#mesh = Mesh('nats://localhost')
#mesh = Mesh('mqtt://localhost')
#mesh = Mesh('redis://localhost/12')
#mesh = Mesh('amqp://slowdash:slowdash@localhost/SlowMesh')
    

@mesh.on('chat.>')
async def handle(headers, data):
    print(f'{headers}: {data}')

    
async def main():
    print('type ctrl-d to stop')
    await mesh.aio_start()
    
    while True:
        try:
            line = await asyncio.to_thread(input)
        except:
            break
        await mesh.aio_publish('chat.to/all', line, headers={'sender':'me'})

    await mesh.aio_close()

    
asyncio.run(main())
