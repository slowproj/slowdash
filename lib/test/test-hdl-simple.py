#! /bin/env python3

from slowpy.control.hdl import *

class TestModule(Module):
    def __init__(self, clock, a, b):
        super().__init__(clock)
        
        self.a = reg()
        self.b = reg()

        self.a <= 'A'
        self.b <= 'B'

        
    @always
    def swap_ab(self):
        self.a <= self.b
        self.b <= self.a

        print(self.a, self.b)
        

        
clock = Clock(Hz=1)
counter = TestModule(clock, a, b)

clock.start()
