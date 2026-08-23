ip = '192.168.50.103'
firmware_version = 1825


from slowpy.control import control_system as ctrl

async def main():
    modbus = ctrl.import_control_module('Modbus').modbus(ip)
    modbus.import_control_module('NanotechMotor')
    c5e = modbus.nanotech_C5E()
    print('C5E Firmware Version: %s' % firmware_version)
    print(c5e.id().get())
    
    try:
        await c5e.cia402.initialize()
    except Exception as e:
        print(f'ERROR: {e}')
        return

    await c5e.auto_setup_mode().aio_set(True)
    
    status = await c5e.status().aio_get()
    error = await c5e.error().aio_get()
    print('Status: %s' % status)
    print('Error Flags: %s' % error)
    
    if ',TARG,' in status:
        print('Encoder index found')
    else:
        print('Encoder index not found')
    if ',OMS1,' in status or ',OMS3,' in status:
        print('Auto Setup completed')
    else:
        print('ERROR: Auto Setup not completed')
        
    await c5e.cia402.switch_off()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
