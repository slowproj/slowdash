ip = '192.168.50.176'
firmware_version = 1825

from slowpy.control import control_system as ctrl


async def main():
    modbus = ctrl.import_control_module('Modbus').modbus(ip)
    modbus.import_control_module('NanotechMotor')
    c5e = modbus.nanotech_C5E(firmware_version=firmware_version)
    print('C5E Firmware Version: %s' % firmware_version)
    
    try:
        await c5e.cia402.initialize()
    except Exception as e:
        print(f'ERROR: {e}')
        return

    await c5e.auto_setup_mode().aio_set(True)
    
    state = await c5e.status().aio_get()
    print('State: %s' % await c5e.status().aio_get())
    if ',TARG,' in state:
        print('Encoder index was found')
    else:
        print('Encoder index not found')
    if ',OMS1,' in state or ',OMS3,' in state:
        print('Auto Setup completely executed')
    else:
        print('ERROR: Auto Setup not completely executed')
        
    await c5e.cia402.switch_off()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
