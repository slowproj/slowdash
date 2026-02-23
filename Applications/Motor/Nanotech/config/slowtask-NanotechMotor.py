
import asyncio, re
import slowpy.control

c5e = None

async def _initialize(params):
    global c5e

    ip = params.get('IP', None)
    if ip is None:
        mac = params.get('MAC', None)
        if mac is not None:
            ip = slowpy.control.IPFinder().find(mac, use_arp_cache=False)
    if ip is None:
        raise slowpy.control.ControlException('Unable to find Nanotech Motor Controller')
    print(f'Nanotech Controller at {ip}')

    ctrl = slowpy.control.control_system
    modbus = ctrl.import_control_module('Modbus').modbus(ip)
    modbus.import_control_module('NanotechMotor')
    c5e = modbus.nanotech_C5E()

    await ctrl.aio_export(c5e.position(), "position")
    await ctrl.aio_export(c5e.status(), "status")
    
    print('Initial State: %s' % await c5e.status().aio_get())
    await c5e.cia402.initialize()


    
async def sd_move(mode:str, steps_deg:float=0, duration_sec:float=0, velocity_rpm:float=None):
    if velocity_rpm is None:
        velocity_rpm = 120
    if mode == 'position':
        if steps_deg == 0:
            await c5e.do_halt()
        else:
            await c5e.profile_position_mode(max_velocity=velocity_rpm).aio_set(steps_deg)
    elif mode == 'velocity':
        if velocity_rpm == 0:
            await c5e.do_halt()
        else:
            await c5e.velocity_mode(velocity=velocity_rpm).aio_set(duration_sec)
    else:
        await c5e.do_halt()

        
async def sd_halt():
    await c5e.do_halt()

    
async def sd_switch_off():
    await c5e.cia402.switch_off()

    

async def _get_html():
    html = f'''
    | <form>
    |   <table>
    |     <tr><td>Step (deg)</td><td><input name="steps_deg"></td></tr>
    |     <tr><td>Speed (rpm)</td><td><input name="velocity_rpm"></td></tr>
    |     <tr><td></td><td>
    |       <input type="submit" name="parallel NanotechMotor.sd_move()" value="Spin">
    |       <input type="submit" name="parallel NanotechMotor.sd_switch_off()" value="Switch Off">
    |     </td></tr>
    |   </table>
    | </form>
    '''
    return re.sub('^[ ]*\\|', '', html, flags=re.MULTILINE)
    

    
if __name__ == '__main__':
    from slowpy.dash import Tasklet
    Tasklet().run()
