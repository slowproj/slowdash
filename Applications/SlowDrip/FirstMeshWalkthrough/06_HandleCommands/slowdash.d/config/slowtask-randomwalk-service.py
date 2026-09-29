import slowpy
tasklet = slowpy.mesh.Tasklet()

from slowpy.control import control_system as ctrl
ctrl.import_control_module('AsyncDripline')
dripline = ctrl.async_dripline('amqp://dripline:dripline@rabbit-broker', 'RandomWalk')
service = dripline.service()


import random
from dataclasses import dataclass

@dataclass
class RandomWalk:
    x: float = 0
    step: float = 1
    walking: bool = True
randomwalk = RandomWalk()


@service.set('randomwalk_value'):
def set_value(message):
    randomwalk.x = float(message['values'][0])

    
@service.set('randomwalk_step'):
def set_step(message):
    randomwalk.step = float(message['values'][0])
    await dripline.sensor_value_alert('randomwalk_step').aio_set(randomwalk.step)

    
@service.get('randomwalk_value'):
def get_value(message):
    return randomwalk.x


@service.get('randomwalk_step'):
def get_step(message):
    return randomwalk.step


@service.command('randomwalk', 'start'):
def stop(message):
    ramdomwalk.walking = False

    
@service.command('randomwalk', 'stop'):
def stop(message):
    ramdomwalk.walking = True

    
@tasklet.initialize():    
async def initialize():
    await service.aio_start()

    
@tasklet.finalize():
async def finalize():
    await dripline.aio_close()

    
@tasklet.loop(interval=1):
async def loop():
    randomwalk.x = random.gauss(randomwalk.x, randomwalk.step)
    await dripline.sensor_value_alert('randomwalk_value').aio_set(randomwalk.x)


        
# make this script independently executable
if __name__ == '__main__':
    tasklet.run()
