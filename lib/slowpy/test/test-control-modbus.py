
#host = '192.168.50.63', 502
host, port = 'localhost', 1502

from slowpy.control import control_system as ctrl
modbus = ctrl.import_control_module('Modbus').modbus(host, port)

reg0 = modbus.register32(0x10)
reg1 = modbus.register32(0x11)

reg0 <= 0x12345678
reg1 <= 0xabcdef00

import time

while True:
    reg0 <= reg0.get() + 1
    reg1 <= reg1.get() + 1

    print(hex(reg0.get()))
    print(hex(reg1.get()))

    time.sleep(1)
    
