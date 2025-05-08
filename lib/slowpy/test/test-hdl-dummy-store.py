
from slowpy.control import ControlSystem
ControlSystem.import_control_module('DummyDevice')
ctrl = ControlSystem()

device = ctrl.randomwalk_device()
store = ctrl.data_store(url='sqlite:///TestHdlDummyStore.db', table='slow_data')


from slowpy.control.hdl import *

class MyReadoutModule(Module):
    def __init__(self, clock, src, dest):
        super().__init__(clock)
        self.src = input_reg(src)
        self.dest = output_reg(dest)
                
    @always
    def do(self):
        self.dest <= self.src
        print(self.src)
        
clock = Clock(Hz=1)
module = MyReadoutModule(
    clock,
    src = device.ch(0),
    dest = store.tag('ch0')
)

clock.start()
