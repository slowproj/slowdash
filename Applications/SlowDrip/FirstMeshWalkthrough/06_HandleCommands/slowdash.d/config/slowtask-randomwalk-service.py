
import asyncio, random

print(f'hello from {__name__}')

from slowpy.control import control_system as ctrl
ctrl.import_control_module('AsyncDripline')
dripline = ctrl.async_dripline('amqp://dripline:dripline@rabbit-broker', 'RandomWalk')


class RandomwalkService:
    def __init__(self):
        self.x = 0
        self.step = 1

    async def on_set(self, message):
        endpoint, value = message.parameters["routing_key"], message.body
        if endpoint == 'randomwalk_value':
            self.x = float(value['values'][0])
            return self.x
        elif endpoint == 'randomwalk_step':
            self.step = abs(float(value['values'][0]))
            await dripline.sensor_value_alert('randomwalk_step').aio_set(self.step)
            return self.step
            
    async def on_get(self, message):
        endpoint, value = message.parameters["routing_key"], message.body
        if endpoint == 'randomwalk_value':
            return self.x
        elif endpoint == 'randomwalk_step':
            return self.step

    async def on_command(self, message):
        endpoint, specifier, value = message.parameters["routing_key"], message.header['specifier'], message.body
        return value
    
    async def run(self):
        await dripline.sensor_value_alert('randomwalk_step').aio_set(self.step)
        while not ctrl.is_stop_requested():
            self.x = random.gauss(self.x, self.step)
            await dripline.sensor_value_alert('randomwalk_value').aio_set(self.x)
            await ctrl.aio_sleep(1)

            
service = RandomwalkService()

async def _run():
    await asyncio.gather(
        dripline.service(service, endpoints=['randomwalk_value', 'randomwalk_step']).aio_start(),
        service.run()
    )

async def _finalize():
    await dripline.aio_close()


    
# make this script independently executable
if __name__ == '__main__':
    from slowpy.dash import Tasklet
    Tasklet().run()
