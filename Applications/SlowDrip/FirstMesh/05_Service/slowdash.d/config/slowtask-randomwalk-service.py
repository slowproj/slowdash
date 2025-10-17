
import asyncio, random, logging

from slowpy.control import control_system as ctrl
ctrl.import_control_module('AsyncDripline')

print(f'hello from {__name__}')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')



class RandomwalkService:
    def __init__(self):
        self.x = 0
        self.step = 1

        
    async def on_set(self, message):
        endpoint, value = message.parameters["routing_key"], message.body
        logging.debug(f'SET {endpoint}: {value}')
        
        if endpoint == 'randomwalk_step':
            self.step = abs(float(value['values'][0]))
            await dripline.sensor_value_alert('randomwalk_step').aio_set(self.step)
            return True
        if endpoint == 'randomwalk':
            self.x = float(value['values'][0])
            return True
            
        
    async def on_get(self, message):
        endpoint, value = message.parameters["routing_key"], message.body
        logging.debug(f'GET {endpoint}: {value}')
        
        if endpoint == 'randomwalk_step':
            return self.step
        if endpoint == 'randomwalk':
            return self.x

        
    async def on_command(self, message):
        endpoint, value = message.parameters["routing_key"], message.body
        logging.debug(f'CMD {endpoint}: {value}')
        
        return True

    
    async def run(self):
        await dripline.sensor_value_alert('randomwalk_step').aio_set(self.step)
        while not ctrl.is_stop_requested():
            self.x = random.gauss(self.x, self.step)
            await dripline.sensor_value_alert('randomwalk').aio_set(self.x)
            await ctrl.aio_sleep(1)


            
service = RandomwalkService()


async def _run():
    await asyncio.gather(
        dripline.service(service, endpoints='*').aio_start(),
        service.run()
    )


async def _finalize():
    await dripline.aio_close()



if __name__ == '__main__':
    from slowpy.dash import Tasklet
    Tasklet().run()
