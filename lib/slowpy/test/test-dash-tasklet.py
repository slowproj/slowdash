
from slowpy.dash import Tasklet
tasklet = Tasklet()
    

@tasklet.on('data.*')
async def handle(headers, data):
    print(f'{headers}: {data}')


@tasklet.loop(interval=3)
async def hello():
    print('hello')
    
    
@tasklet.once(delay=5)
def late():
    print("I'm joining now")

          
@tasklet.once()
async def publish():
    import asyncio, random
    
    x = 0
    while not tasklet.is_stop_requested():
        x += random.gauss(0, 1)
        await tasklet.aio_publish('data.randomwalk', x)
        await asyncio.sleep(1)


if __name__ == '__main__':
    #mesh = None
    mesh = 'slowmq://localhost:18881'
    #mesh = 'nats://localhost'
    #mesh = 'mqtt://localhost'
    #mesh = 'redis://localhost/12'
    #mesh = 'amqp://slowdash:slowdash@localhost/SlowMesh'

    tasklet.run(mesh_url=mesh)
