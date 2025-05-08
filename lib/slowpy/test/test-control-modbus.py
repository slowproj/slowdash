
host = '192.168.50.63'

from slowpy.control import control_system as ctrl
modbus = ctrl.import_control_module('Modbus').modbus(host)

interval = modbus.holding_register(0)
dout0 = modbus.holding_register(1)
dout1 = modbus.holding_register(2)
din = modbus.input_register(0)



import time

interval <= 700
dout0 <= 0x5a5a
dout1 <= 0xa5a5

for i in range(12):
    print(din)
    time.sleep(0.2)
