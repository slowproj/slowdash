
import asyncio
from slowpy.dash import Mesh

#mesh_url = None
#mesh_url = 'slowmq://localhost:18881'
mesh_url = 'nats://localhost'
#mesh_url = 'mqtt://localhost'
#mesh_url = 'redis://localhost/12'
#mesh_url = 'amqp://slowdash:slowdash@localhost/SlowMesh'

mesh = Mesh(mesh_url)


import datetime

@mesh.export
def chat(*args, **kwargs):
    print(f"hello, you gave me {args} and {kwargs}")
    print(f"I will tell you the current time")
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
            print(await mesh.aio_call('test-dash-mesh-rpc.chat', line, sender='me'))
        
    await mesh.aio_close()


if __name__ == '__main__':
    asyncio.run(main())
