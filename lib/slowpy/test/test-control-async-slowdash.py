
from slowpy.control import control_system as ctrl
http = ctrl.async_http('http://localhost:18881')
slowdash = http.import_control_module('AsyncSlowdash').async_slowdash()


async def main():
    print("ping -> ", await slowdash.ping().aio_get())
    print("config -> ", await slowdash.config().aio_get())
    print("channels -> ", await slowdash.channels().aio_get())
    

    print(await slowdash.config_file('slowplot-trash.json').aio_set('{"message": "hello"}'))
    print(await slowdash.config_file('slowplot-trash.json').aio_get())
    
    
    ctrl.stop_by_signal()
    while not ctrl.is_stop_requested():
        try:
            print("data/ch0,ch1 -> ", await slowdash.data('ch0,ch1',length=60).aio_get())
        except Exception:
            pass
    
        await ctrl.aio_sleep(1)
    

import asyncio
asyncio.run(main())
