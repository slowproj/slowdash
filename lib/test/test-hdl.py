#! /bin/env python3


import time
import slowpy.control as spc


ctrl = spc.ControlSystem()    
start_btn = ctrl.value(False).oneshot()
stop_btn = ctrl.value(False).oneshot()
clear_btn = ctrl.value(False).oneshot()
display = ctrl.value()

def _export():
    return [
        ('start', start_btn.writeonly()),
        ('stop', stop_btn.writeonly()),
        ('clear', clear_btn.writeonly()),
        ('display', display.readonly())
    ]


from slowpy.control.hdl import *

class CounterModule(Module):
    def __init__(self, clock, start, stop, clear, display):
        super().__init__(clock)
        
        self.start = inp(start)
        self.stop = inp(stop)
        self.clear = inp(clear)
        self.display = outp(display)
        self.counter = reg()
        self.running = reg()

        self.counter <= 0
        self.running <= 0
                

    @always
    def startstop(self):
        if self.stop:
            self.running <= False
        elif self.start:
            self.running <= True

    @always
    def count(self):
        if self.clear:
            self.counter <= 0
        elif self.running:
            if self.counter == 15:
                self.counter <= 0
            else:
                self.counter <= int(self.counter) + 1

    @always
    def show_internals(self):
        print(self.start, self.stop, self.clear, self.counter)
        

        
clock = Clock(Hz=1)
counter = CounterModule(
    clock,
    start = start_btn,
    stop = stop_btn,
    clear = clear_btn,
    display = display
)

clock.start()

time.sleep(2)
start_btn.set(True)
time.sleep(5)
stop_btn.set(True)
time.sleep(5)
start_btn.set(True)
time.sleep(3)
clear_btn.set(True)
time.sleep(5)
clock.stop()
