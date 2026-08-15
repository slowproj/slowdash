# control_NanotechMotor.py

import time, asyncio, logging
import slowpy.control as spc


class Nanotech_C5E(spc.ControlNode):
    class WriteRegisters:
        def __init__(self, modbus, firmware_version):
            if firmware_version <= 2039:
                offset_after_6002 = 2
            else:
                offset_after_6002 = 0

            self.control = modbus.register(6000)
            self.mode = modbus.register(6001)
            self.position_h = modbus.register(6002 + offset_after_6002)
            self.position_l = modbus.register(6003 + offset_after_6002)
            self.max_velocity_h = modbus.register(6004 + offset_after_6002)
            self.max_velocity_l = modbus.register(6005 + offset_after_6002)
            self.velocity = modbus.register(6006 + offset_after_6002)

            self.MODE_AUTOSETUP = 0x00fe
            self.MODE_PROFILEPOSITION = 1
            self.MODE_VELOCITY = 2
            #self.MODE_PROFILEVELOCITY = 3  # not in the default mapping

            # CiA402 state machine bits are hard-coded below
            self.CTRL_OPERATION = 0x000f
            self.CTRL_RELATIVE = 0x0040
            self.CTRL_START = 0x0010
            self.CTRL_HALT = 0x0100

        async def write_control(self, ctrl:int):
            self.control.set(ctrl)
            await asyncio.sleep(0.1)
            
        async def write_mode(self, mode:int):
            self.mode.set(mode)
            await asyncio.sleep(0.1)
            
        async def write_position(self, position:int):
            self.position_h.set((position >> 16) & 0xffff)
            await asyncio.sleep(0.1)
            self.position_l.set(position & 0xffff)
            await asyncio.sleep(0.1)
            
        async def write_max_velocity(self, velocity:int):
            self.max_velocity_h.set((velocity >> 16) & 0xffff)
            await asyncio.sleep(0.1)
            self.max_velocity_l.set(velocity & 0xffff)
            await asyncio.sleep(0.1)
            
        async def write_velocity(self, velocity:int):
            self.velocity.set(velocity & 0xffff)
            await asyncio.sleep(0.1)
            
            
    class ReadRegisters:
        def __init__(self, modbus, firmware_version):
            self.status = modbus.register(5000)
            self.mode = modbus.register(5001)
            self.error = modbus.register(4997)
            self.position_h = modbus.register(5002)
            self.position_l = modbus.register(5003)
            self.velocity = modbus.register(5004)

            self.STATBIT_REACHED = 10
            self.STATBIT_AUTOSETUP_COMPLETE = 12

            
        async def read_mode(self):
            return self.mode.get()

        async def read_status(self):
            return self.status.get()

        async def read_error(self):
            return self.error.get()

        async def read_position(self):
            position_h = self.position_h.get()
            position_l = self.position_l.get()
            if position_h is None or position_l is None:
                return None
            else:
                return (self.position_h.get() << 16) | self.position_l.get()

        async def read_velocity(self):
            return self.velocity.get()

        async def wait_for_status(self, bit_index, expected_value=1):
            while True:
                status = await self.read_status()
                if status is None:
                    return False
                if ((status >> bit_index) & 1) == expected_value:
                    break
                await asyncio.sleep(0.1)
            return True


    class CiA402:
        def __init__(self, wreg, rreg):
            self.wreg = wreg
            self.rreg = rreg
            self.status = None
            
        async def is_ready_to_switch_on(self):
            if self.status is None:
                self.status = await self.rreg.read_status()
                if self.status is None:
                    return False
            return (self.status & 0x06) == 0x06

        async def is_switched_on(self):
            if self.status is None:
                self.status = await self.rreg.read_status()
                if self.status is None:
                    return False
            return (self.status & 0x07) == 0x07

        async def is_operation_enabled(self):
            if self.status is None:
                self.status = await self.rreg.read_status()
                if self.status is None:
                    return False
            return (self.status & 0x0f) == 0x0f
    
        async def initialize(self):
            await self.wreg.write_control(0x0000)
            self.status = 0
            logging.info("Nanotech_C5E: Initialized")

        async def be_ready_to_switch_on(self):
            if not await self.is_ready_to_switch_on():
                await self.wreg.write_control(0x0006)
                self.status = 0x0006
                logging.info("Nanotech_C5E: Ready to Switch-On")
                
        async def switch_on(self):
            await self.be_ready_to_switch_on()
            if not await self.is_switched_on():
                await self.wreg.write_control(0x0007)
                self.status = 0x0007
                logging.info("Nanotech_C5E: Switched On")
                
        async def enable_operation(self):
            await self.switch_on()
            if not await self.is_operation_enabled():
                await self.wreg.write_control(0x000f)
                self.status = 0x000f
                logging.info("Nanotech_C5E: Operation Enabled")
                
        async def disable_operation(self):
            if await self.is_operation_enabled():
                await self.wreg.write_control(0x0007)
                self.status = 0x0007
                logging.info("Nanotech_C5E: Operation Disabled")
                
        async def switch_off(self):
            if await self.is_switched_on():
                await self.wreg.write_control(0x0006)
                self.status = 0x0006
                logging.info("Nanotech_C5E: Switched Off")
                
            
    def __init__(self, modbus):
        self.modbus = modbus

        self.id_node = NanotechC5E_IdNode(self)
        id_firmware = self.id_node.get().get('firmware_version', '')
        if id_firmware.startswith('FIR-v'):
            firmware_version = int(id_firmware[len('FIR_v'):len('FIR_v2213')])
        else:
            firmware_version = 2213
        
        self.wreg = Nanotech_C5E.WriteRegisters(modbus, firmware_version)
        self.rreg = Nanotech_C5E.ReadRegisters(modbus, firmware_version)
        self.cia402 = Nanotech_C5E.CiA402(self.wreg, self.rreg)

        self.current_mode = None
        self.is_moving = False

        self.position_node = NanotechC5E_PositionNode(self)
        self.velocity_node = NanotechC5E_VelocityNode(self)
        self.status_node = NanotechC5E_StatusNode(self)
        self.error_node = NanotechC5E_ErrorNode(self)
    
    # nanotech_C5E().auto_setup_mode().aio_set(go:bool)
    def auto_setup_mode(self):
        return NanotechC5E_AutoSetupModeNode(self)

    # nanotech_C5E().profile_position_mode(max_velocity_rpm:float).aio_set(steps_deg:float)
    def profile_position_mode(self, *, max_velocity=500):
        return NanotechC5E_ProfilePositionModeNode(self, max_velocity=max_velocity)

    # nanotech_C5E().velocity_mode(velocity_rpm:float).aio_set(duration_sec:float)
    def velocity_mode(self, velocity):
        return NanotechC5E_VelocityModeNode(self, velocity)

    # nanotech_C5E().position(): returns the current position in degree
    def position(self):
        return self.position_node

    # nanotech_C5E().velocity(): returns the current velocity in rpm
    def velocity(self):
        return self.velocity_node

    # nanotech_C5E().id()
    def id(self):
        return self.id_node

    # nanotech_C5E().status()
    def status(self):
        return self.status_node

    # nanotech_C5E().error()
    def error(self):
        return self.error_node

    
    @classmethod
    def _node_creator_method(cls):
        def nanotech_C5E(self):
            if self.__class__.__name__ != 'ModbusNode':
                raise spc.ControlException('Nanotech_C5E must be attached to a Modbus Node')
            try:
                self.nanotech_C5E_node
            except:
                self.nanotech_C5E_node = Nanotech_C5E(self)
            return self.nanotech_C5E_node

        return nanotech_C5E


    async def do_autoset(self):
        print('### Auto setup ###')
        print('Make sure')
        print('- Parameters are correctly setup in the device "cfg" file')
        print('- The motor is load-free')
    
        await self.cia402.initialize()
        await self.wreg.write_mode(self.wreg.MODE_AUTOSETUP)
        self.current_mode =self.wreg.MODE_AUTOSETUP
        
        await self.cia402.enable_operation()
    
        await self.wreg.write_control(self.wreg.CTRL_START | self.wreg.CTRL_OPERATION)
        print('Nanotech_C5E: running auto_setup...')
    
        await self.rreg.wait_for_status(self.rreg.STATBIT_AUTOSETUP_COMPLETE)
        print('Nanotech_C5E: auto_setup completed')
    
        await self.cia402.initialize()
        print('IMPORTANT: power cycle the controller device')
    

    async def do_profile_position(self, steps:int, max_velocity:int):
        if self.is_moving:
            await self.do_halt()
            
        if self.current_mode != self.wreg.MODE_PROFILEPOSITION:
            # mode can be changed even during operation-enabled            
            await self.wreg.write_mode(self.wreg.MODE_PROFILEPOSITION)

        await self.cia402.disable_operation()
        await self.wreg.write_max_velocity(int(max_velocity))
        await self.wreg.write_position(int(steps))
        await self.cia402.enable_operation()
    
        self.is_moving = True
        await self.wreg.write_control(self.wreg.CTRL_RELATIVE | self.wreg.CTRL_OPERATION)
        await self.wreg.write_control(self.wreg.CTRL_START | self.wreg.CTRL_RELATIVE | self.wreg.CTRL_OPERATION)
        logging.info(f'Nanotech_C5E: running in profile position mode: steps={steps}')
    
        await self.rreg.wait_for_status(self.rreg.STATBIT_REACHED) # wait for completion
        
        if self.is_moving:
            await self.do_halt()
        logging.info(f'Nanotech_C5E: profile position mode completed')


    async def do_velocity(self, velocity:int, duration:float):
        if self.is_moving:
            await self.do_halt()
            
        if self.current_mode != self.wreg.MODE_VELOCITY:
            # mode can be changed even during operation-enabled            
            await self.wreg.write_mode(self.wreg.MODE_VELOCITY)  
        await self.cia402.enable_operation()

        logging.info(f'Nanotech_C5E: running in velocity mode: volocity={velocity}')
        self.is_moving = True
        await self.wreg.write_control(self.wreg.CTRL_OPERATION)
        await self.wreg.write_velocity(int(velocity))

        if duration <= 0:
            return
        end_time = time.monotonic() + duration
        while self.is_moving and time.monotonic() < end_time:
            await asyncio.sleep(0.1)

        if self.is_moving:
            await self.do_halt()

        
    async def do_halt(self):
        if await self.cia402.is_operation_enabled():
            await self.wreg.write_control(self.wreg.CTRL_HALT | self.wreg.CTRL_OPERATION)
        self.is_moving = False
        logging.info(f'Nanotech_C5E: halted')

        
    async def do_switch_off(self):
        await self.cia402.switch_off()
        self.is_moving = False

        
    async def do_read_position(self):
        return await self.rreg.read_position()

        
    async def do_read_velocity(self):
        return await self.rreg.read_velocity()

        
        
class NanotechC5E_AutoSetupModeNode(spc.ControlVariableNode):
    def __init__(self, c5e):
        self.c5e = c5e

    async def aio_set(self, go:bool):
        if go:
            await self.c5e.do_autoset()
    

            
class NanotechC5E_ProfilePositionModeNode(spc.ControlVariableNode):
    def __init__(self, c5e, *, max_velocity:float=500):
        self.c5e = c5e
        self.max_velocity = int(abs(max_velocity))

    async def aio_set(self, steps_deg:float):
        steps = int(10*steps_deg)
        if steps < 0:
            steps = 0x100000000 + steps  # signed 32bit
        await self.c5e.do_profile_position(steps, self.max_velocity)

    async def aio_get(self):
        await self.c5e.do_read_position() / 10.0  # to degrees

        
        
class NanotechC5E_VelocityModeNode(spc.ControlVariableNode):
    def __init__(self, c5e, velocity:float):
        self.c5e = c5e
        if velocity < 0:
            self.velocity = 0x10000 + int(velocity)  # signed 16bit
        else:
            self.velocity = int(velocity)

    async def aio_set(self, duration:float):
        await self.c5e.do_velocity(self.velocity, duration)


        
class NanotechC5E_PositionNode(spc.ControlVariableNode):
    def __init__(self, c5e):
        self.c5e = c5e

    async def aio_get(self):
        position = await self.c5e.do_read_position()
        if position is None:
            return None
        else:
            if position < 0x80000000:
                return position / 10.0  # deg
            else:
                return (position-0x100000000) / 10.0  # deg


class NanotechC5E_VelocityNode(spc.ControlVariableNode):
    def __init__(self, c5e):
        self.c5e = c5e

    async def aio_get(self):
        velocity = await self.c5e.do_read_velocity()
        if velocity is None:
            return None
        else:
            # signed 16bit
            if velocity < 0x8000:
                return velocity
            else:
                return velocity - 0x10000


class NanotechC5E_IdNode(spc.ControlVariableNode):
    def __init__(self, c5e):
        try:
            ip = c5e.modbus.host
            http = spc.control_system.http(f'http://{ip}')
            self.id = {
                'model': http.path('/od/1008/00').json().get(),
                'hardware_version': http.path('/od/1009/00').json().get(),
                'firmware_version': http.path('/od/100a/00').json().get(),
                'MAC': http.path('/od/200f/00').json().get(),
            }
        except Exception as e:
            logging.error(f'NanotechC5E: {e}')
            self.id = {}
            

    def get(self):
        return self.id
        
    async def aio_get(self):
        return self.id
        

class NanotechC5E_StatusNode(spc.ControlVariableNode):
    def __init__(self, c5e):
        self.c5e = c5e

    async def aio_get(self):
        mode = await self.c5e.rreg.read_mode()
        status_code = await self.c5e.rreg.read_status()            
        
        if mode is None or status_code is None:
            return 'NO_RESPONSE'
            
        status = []
        if mode == self.c5e.wreg.MODE_AUTOSETUP:
            status.append('AUTO_SETUP')
        elif mode == self.c5e.wreg.MODE_PROFILEPOSITION:
            status.append('PROFILE_POS')
        elif mode == self.c5e.wreg.MODE_VELOCITY:
            status.append('VELOCITY')
        elif mode == 0:
            status.append(f'NO_MODE')
        else:
            status.append(f'UNKNOWN_MODE_{mode}')
        
        status.append('CLA' if status_code & 0x8000 else '-')
        status.append('OMS%01d' % ((status_code >> 12) & 0x03))
        status.append('ILA' if status_code & 0x0800 else '-')
        status.append('TARG' if status_code & 0x0400 else '-')
        status.append('REM' if status_code & 0x0200 else '-')
        status.append('SYNC' if status_code & 0x0100 else '-')
        status.append('WARN' if status_code & 0x0080 else '-')
        status.append('SOD' if status_code & 0x0040 else '-')
        status.append('-' if status_code & 0x0020 else 'QS')
        status.append('VE' if status_code & 0x0010 else '-')
        status.append('FAULT' if status_code & 0x0008 else '-')
        status.append('OE' if status_code & 0x0004 else '-')
        status.append('SO' if status_code & 0x0002 else '-')
        status.append('RTSO' if status_code & 0x0001 else '-')

        status.append('MOVING' if self.c5e.is_moving else '-')
        
        return f'{status_code:04x}h:{",".join(status)}'
        

class NanotechC5E_ErrorNode(spc.ControlVariableNode):
    def __init__(self, c5e):
        self.c5e = c5e

    async def aio_get(self):
        error_code = await self.c5e.rreg.read_error()
        if error_code == 0:
            return '00h: No errors'
            
        errors = []
        if (error_code >> 0) & 0x01: error.append('Watchdog reset')
        if (error_code >> 1) & 0x01: error.append('Input voltage too high')
        if (error_code >> 2) & 0x01: error.append('Output current too high')
        if (error_code >> 3) & 0x01: error.append('Input voltage too low')
        if (error_code >> 4) & 0x01: error.append('Field-bus error')
        if (error_code >> 5) & 0x01: error.append('-')
        if (error_code >> 6) & 0x01: error.append('CANopen NMT error')
        if (error_code >> 7) & 0x01: error.append('Sensor 1 defective')
        if (error_code >> 8) & 0x01: error.append('Sensor 2 defective')
        if (error_code >> 9) & 0x01: error.append('Sensor 3 defect')
        if (error_code >> 10) & 0x01: error.append('Positive limit exceeded')
        if (error_code >> 11) & 0x01: error.append('Negative lmit exceeded')
        if (error_code >> 12) & 0x01: error.append('Overtemperature')
        if (error_code >> 13) & 0x01: error.append('???')
        if (error_code >> 14) & 0x01: error.append('Memory full')
        if (error_code >> 15) & 0x01: error.append('MotorBlocked')

        return f'{error_code:02x}h: {",".join(errors)}'
        

if __name__ == '__main__':
    ip = '192.168.50.176'
    logging.basicConfig(level=logging.INFO)
    
    async def main(ip):    
        from slowpy.control import control_system as ctrl
        modbus = ctrl.import_control_module('Modbus').modbus(ip)
        c5e = modbus.import_control_module('NanotechMotor').nanotech_C5E()
        
        print('Initial State: %s' % await c5e.status().aio_get())
        try:
            await c5e.cia402.initialize()
        except Exception as e:
            print(f"ERROR: {e}")
            return

        start_time = time.time()
        start_position = await c5e.position().aio_get()
        print(await c5e.status().aio_get())
    
        await c5e.auto_setup_mode().aio_set(True)
        #await c5e.profile_position_mode(max_velocity=2*60).aio_set(2*360*3)
        #await c5e.velocity_mode(-120).aio_set(3)
    
        #await c5e.cia402.disable_operation()
        await c5e.cia402.switch_off()
        
        stop_time = time.time()
        stop_position = await c5e.position().aio_get()
        print("Lapse: ", stop_time-start_time)
        print("Move: ", start_position, " -> ", stop_position, ": ", (stop_position-start_position))
        print(await c5e.status().aio_get())

    asyncio.run(main(ip))
