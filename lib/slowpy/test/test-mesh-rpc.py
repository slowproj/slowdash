
import asyncio, datetime
from slowpy.mesh import Mesh

#mesh_url = None
mesh_url = 'slowmq://localhost:18881'
#mesh_url = 'nats://localhost'
#mesh_url = 'mqtt://localhost'
#mesh_url = 'redis://localhost/12'
#mesh_url = 'amqp://slowdash:slowdash@localhost/SlowMesh'

mesh = Mesh(mesh_url)


@mesh.export
def chat(line, *, sender=None):
    print(f'You ("{sender}") sent me "{line}".')
    print(f'I will send you the current time.')
    return str(datetime.datetime.now())


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
                print(await mesh.aio_call('test-mesh-rpc.chat', line, sender=mesh.mesh_id))
            except Exception as e:
                print(f'ERROR: {e}')
        
    await mesh.aio_close()


if __name__ == '__main__':
    asyncio.run(main())
