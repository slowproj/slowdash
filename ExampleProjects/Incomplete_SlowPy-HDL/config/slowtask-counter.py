
import slowpy.control as spc

ctrl = spc.ControlSystem()    
start_btn = ctrl.value(False).oneshot()
stop_btn = ctrl.value(False).oneshot()
clear_btn = ctrl.value(False).oneshot()
display = ctrl.value()


### Slow-HDL ###

from slowpy.control.hdl import *

class CounterModule(Module):
    def __init__(self, clock, start, stop, clear, count):
        super().__init__(clock)
        
        # binding to registers #
        self.start = inp(start)
        self.stop = inp(stop)
        self.clear = inp(clear)
        self.count = outp(count)
        self.running = reg()

        # register initialization #
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
            if self.count == 32:
                self.count <= 0
            else:
                self.count <= int(self.count) + 1

    @always
    def show_internals(self):
        print(self.start, self.stop, self.clear, self.count)
        

        
clock = Clock(Hz=1)
counter = CounterModule(
    clock,
    start = start_btn,
    stop = stop_btn,
    clear = clear_btn,
    count = display
)



### SlowTask interface ###

def _initialize(params={}):
    start_btn.set(True)
    

def _run():
    clock.start()
    clock.join()

    
def _halt():
    clock.stop()

    
def _export():
    return [
#        ('start', start_btn.writeonly()),
#        ('stop', stop_btn.writeonly()),
#        ('clear', clear_btn.writeonly()),
        ('display', display.readonly())
    ]


    
if __name__ == '__main__':
    import time
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
