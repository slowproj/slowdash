
import asyncio
from slowpy.mesh import Mesh

#mesh_url = None
mesh_url = 'slowmq://localhost:18881'
#mesh_url = 'nats://localhost'
#mesh_url = 'mqtt://localhost'
#mesh_url = 'redis://localhost/12'
#mesh_url = 'amqp://slowdash:slowdash@localhost/SlowMesh'

mesh = Mesh(mesh_url)


@mesh.on('chat.>')
def chat(headers, data):
    print(f'{headers}: {data}')


async def main():
    await mesh.aio_start()
    
    print('type ctrl-d to stop')
    while True:
        try:
            line = await asyncio.to_thread(input)
        except:
            break
        else:
            try:
                #await mesh.aio_publish('chat.all', line, headers={'sender':mesh.mesh_id})
                mesh.publish('chat.all', line, headers={'sender':mesh.mesh_id})  # possible, not recommended
            except Exception as e:
                print(f'ERROR: {e}')
            
    await mesh.aio_close()
                

if __name__ == '__main__':
    asyncio.run(main())
