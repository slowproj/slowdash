
from slowpy.control import control_system as ctrl
ctrl.import_control_module('AsyncDripline')

print('hello from randomwalk-service.py')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')
    


class Service:
    pass



service = Service()


async def _run():
    await dripline.service(service).aio_start()


async def _finalize():
    await dripline.aio_close()
    
