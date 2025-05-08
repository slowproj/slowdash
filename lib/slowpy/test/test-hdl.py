
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
    def __init__(self, clock, start, stop, clear, count):
        super().__init__(clock)
        
        self.start = input_reg(start)
        self.stop = input_reg(stop)
        self.clear = input_reg(clear)
        self.count = output_reg(count)
        self.running = reg()

        self.count <= 0
        self.running <= False
                
    @always
    def startstop(self):
        if self.stop:
            self.running <= False
        elif self.start:
            self.running <= True

    @always
    def update(self):
        if self.clear:
            self.count <= 0
        elif self.running:
            if int(self.count) == 32:
                self.count <= 0
            else:
                self.count <= int(self.count) + 1
                
    @always
    def show_internals(self):
        print(self.start, self.stop, self.clear, self.running, self.count)
        print(display)
        

        
clock = Clock(Hz=1)
counter = CounterModule(
    clock,
    start = start_btn,
    stop = stop_btn,
    clear = clear_btn,
    count = display
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
