
import time, re, asyncio
import slowpy.control

ctrl = slowpy.control.control_system
c5e = None
datastore = None

async def _initialize(params):
    global c5e, datastore

    await ctrl.aio_publish("Looking for the device (can take a minute)", name="connection")
    ip = params.get('IP', None)
    if ip is None:
        mac = params.get('MAC', None)
        if mac is not None:
            cidr = params.get('CIDR', None)
            ip = slowpy.control.find_ip(mac, use_arp_cache=False, cidr=cidr)
    if ip is None:
        await ctrl.aio_publish(f"Unable to find the IP address of the controller")
        raise slowpy.control.ControlException('Unable to find Nanotech Motor Controller')
    await ctrl.aio_publish(f"Found at {ip}", name="connection")
    print(f'Nanotech Controller at {ip}')

    modbus = ctrl.import_control_module('Modbus').modbus(ip)
    modbus.import_control_module('NanotechMotor')
    c5e = modbus.nanotech_C5E()

    try:
        print(f'NanotechMotor: Initial State: {await c5e.status().aio_get()}')
        await c5e.cia402.initialize()
    except Exception as e:
        print(f'NanotechMotor: {e}')
        c5e = None

    db_url = params.get('db_url', 'sqlite:///SlowMotor')
    try:
        datastore = slowpy.store.create_datastore_from_url(db_url, 'data')
        print(f"DB connected at {db_url}")
    except Exception as e:
        print(e)
        datastore = None
    if c5e is not None:
        c5e.last_log_time = time.monotonic()
    

async def _loop():
    if c5e is not None:
        position = await c5e.position().aio_get()
        velocity = await c5e.velocity().aio_get()
        await ctrl.aio_publish(position, "position")
        await ctrl.aio_publish(velocity, "velocity")
        await ctrl.aio_publish(c5e.status(), "status")
        if datastore is not None:
            now = time.monotonic()
            if c5e.is_moving or (now - c5e.last_log_time > 10):
                c5e.last_log_time = now
                datastore.append({
                    'position': position,
                    'velocity': velocity,
                })
    await asyncio.sleep(1)
    
    
async def sd_move(mode:str, steps_deg:float=0, duration_sec:float=0, velocity_rpm:float=None):
    if c5e is None:
        return False
    
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
        
    await ctrl.aio_publish(c5e.status(), "status")

        
async def sd_halt():
    if c5e is None:
        return False
    
    await c5e.do_halt()
    await ctrl.aio_publish(c5e.status(), "status")

    
async def sd_switch_off():
    if c5e is None:
        return False
    
    await c5e.do_switch_off()
    await ctrl.aio_publish(c5e.status(), "status")

    

async def _get_html():
    html = f'''
    | <form>
    |   <table>
    |     <tr><td>Connection</td><td colspan="2" ><span sd-value="connection">not connected</span></td></tr>
    |     <tr><td>Status</td><td colspan="2" ><span sd-value="status">unknown</span></td></tr>
    |     <tr><td>Current Position</td><td colspan="2"><span sd-value="position">unknown</span></td></tr>
    |     <tr><td>Current Velocity</td><td colspan="2"><span sd-value="velocity">unknown</span></td></tr>
    |     <tr><td>---</td><td></td><td></td></tr>
    |     <tr><td><label><input type="radio" name="mode" value="position" checked> Step (deg)</label></td><td><input name="steps_deg" value="0"></td><td>(profile position mode)</td></tr>
    |     <tr><td><label><input type="radio" name="mode" value="velocity"> Duration (sec)</label></td><td><input name="duration_sec" value="0"></td><td>(velocity mode)</td></tr>
    |     <tr><td>Velocity (rpm)</td><td><input name="velocity_rpm" value="60"></td></tr>
    |   </table>
    |   <div style="font-size:130%;margin:1em">
    |     <input type="submit" name="parallel NanotechMotor.sd_move()" value="Move">
    |     <input type="submit" name="parallel NanotechMotor.sd_halt()" value="Stop">
    |     <input type="submit" name="parallel NanotechMotor.sd_switch_off()" value="Switch Off">
    |   </div>
    | </form>
    '''
    return re.sub('^[ ]*\\|', '', html, flags=re.MULTILINE)
    

    
if __name__ == '__main__':
    from slowpy.dash import Tasklet
    Tasklet().run()
