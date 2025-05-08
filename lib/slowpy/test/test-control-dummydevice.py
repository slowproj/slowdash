
import time

from slowpy.control import ControlSystem
ControlSystem.import_control_module('DummyDevice')

device = ControlSystem().randomwalk_device()
ch0 = device.ch(0)
ch1 = device.ch(1)
print(f"Walk: {device.walk()}, Decay: {device.decay()}");

for i in range(10):
    print(ch0, ch1)
    time.sleep(1)


ch0.setpoint().set(-10)
ch1.setpoint().set(100)
device.walk().set(0.1)
device.decay().set(1)
print(f"Walk: {device.walk()}, Decay: {device.decay()}");

for i in range(10):
    print(ch0.setpoint(), ch1.setpoint(), ch0, ch1)
    time.sleep(1)
