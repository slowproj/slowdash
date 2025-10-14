
from slowpy.control import control_system as ctrl
ctrl.import_control_module('AsyncDripline')
dripline = ctrl.dripline('amqp://dripline:dripline@localhost')


async def main():
    peaches = dripline.endpoint('peaches')
    chips = dripline.endpoint('chips')
    await peaches.aio_set(1234)

    ctrl.stop_by_signal()
    while not ctrl.is_stop_requested():
        print(await peaches.value_cal().aio_get())
        print(await chips.value_raw().aio_get())
        await ctrl.aio_sleep(1)

        
import asyncio        
asyncio.run(main())
