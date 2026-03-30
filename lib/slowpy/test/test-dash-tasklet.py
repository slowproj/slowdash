
from slowpy.dash import Tasklet
tasklet = Tasklet()
    

@tasklet.initialize()
def _initialize(params):
    print(f"params are {params}")

    
@tasklet.initialize()
def init():
    print("I'm gonna work hard!")

    
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
    
    
    
@tasklet.on('data.>')
def handle(headers, data):
    print(f'{headers}: {data}')

    
import random
x = 0

@tasklet.loop(interval=1.0)
def publish():
    global x
    x += random.gauss(0, 1)
    tasklet.publish('data.randomwalk', x)


    
if __name__ == '__main__':
    #mesh = None
    mesh = 'slowmq://localhost:18881'
    #mesh = 'nats://localhost'
    #mesh = 'mqtt://localhost'
    #mesh = 'redis://localhost/12'
    #mesh = 'amqp://slowdash:slowdash@localhost/SlowMesh'

    tasklet.run(mesh_url=mesh)
