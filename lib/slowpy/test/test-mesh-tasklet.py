
from slowpy.mesh import Tasklet
tasklet = Tasklet()
    

@tasklet.initialize()
def _initialize(params):
    print(f"params are {params}")

    
@tasklet.initialize()
async def get_conf():
    print(await tasklet.dash.aio_get_config())

    
@tasklet.finalize()
def fin():
    print("I'm done.")

    
@tasklet.finalize()
def fin2():
    print("bye!")

    
@tasklet.schedule('0:00,8:00,16:00', use_utc=True)
def alarm():
    print("It's time!")


@tasklet.once(delay=5)
def late():
    print("I'm joining now")


@tasklet.loop(interval=3)
def hello():
    print("I'm still working")
    
    
@tasklet.loop(interval=5)
async def get_data():
    print(await tasklet.dash.aio_get_data('ch0',length=30))

    
@tasklet.mesh.on('data.>')
def handle(headers, data):
    sender = headers.get('sender', 'unknown')
    print(f'{sender} is now at {data}.')

    
import random
x = 0

@tasklet.loop(interval=1.0)
def publish():
    global x
    x += random.gauss(0, 1)
    tasklet.mesh.publish('data.randomwalk', x, headers={'sender':tasklet.mesh.mesh_id})


    
if __name__ == '__main__':
    tasklet.run(slowdash_url='http://localhost:18881')
