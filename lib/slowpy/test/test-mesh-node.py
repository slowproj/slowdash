
from slowpy.mesh import Mesh

#mesh_url = None
mesh_url = 'slowmq://localhost:18881'
#mesh_url = 'nats://localhost'
#mesh_url = 'mqtt://localhost'
#mesh_url = 'redis://localhost/12'
#mesh_url = 'amqp://slowdash:slowdash@localhost/SlowMesh'

mesh = Mesh(mesh_url)


from slowpy.control import ControlNode

class EchoNode(ControlNode):
    def __init__(self):
        self.value = None
    
    def set(self, value):
        self.value = value

    def get(self):
        return f'you said "{self.value}"'

    
mesh.export('echo', EchoNode())



async def main():
    node = mesh.remote_node('test_mesh_node.echo')
    await mesh.aio_start()
    
    print('type ctrl-d to stop')
    while True:
        try:
            line = await asyncio.to_thread(input)
        except:
            break
        else:
            try:
                await node.aio_set(line)
                print(await node.aio_get())
            except Exception as e:
                print(f'ERROR: {e}')
        
    await mesh.aio_close()


    
if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
