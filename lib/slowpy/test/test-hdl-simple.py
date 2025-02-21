#! /bin/env python3

import slowpy.control as spc
from slowpy.control.hdl import *

class TestModule(Module):
    def __init__(self, clock, a, b):
        super().__init__(clock)
        self.a = reg(a)
        self.b = reg(b)
        
    @always
    def swap_ab(self):
        self.a <= self.b
        self.b <= self.a
        print(self.a, self.b)
        

ctrl = spc.ControlSystem()
a = ctrl.value('A')
b = ctrl.value('B')


clock = Clock(Hz=1)
counter = TestModule(clock, a, b)
clock.start()
