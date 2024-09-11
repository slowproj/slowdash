---
title: "SlowPy HDL (experimental)"
---


# Overview
SlowPy HDL enables describing control sequnences in a Verilog-like style. If you are not familiar with Hardware Description Languages (HDL) such as VHDL and Verilog, you will be confused and will hate this. Please do not use this feature in that case. Some people, however, might find this a straightforward way to build parallel concurrent state machines. This feature was originally designed to replace legacy PLC (Programmable Logic Controller) systems with SlowPy; ladder logic can be directly translated to SlowPy HDL processes.


### Example
For a control system that consists of a counter and start / stop buttons:
```python
import slowpy.control as spc

ctrl = spc.ControlSystem()    
start_btn = ctrl.value(False).oneshot()
stop_btn = ctrl.value(False).oneshot()
display = ctrl.value()

def _export():
    return [
        ('start', start_btn.writeonly()),
        ('stop', stop_btn.writeonly()),
        ('display', display.readonly())
    ]
```

The logic to control the conter can be written like this:
```python
from slowpy.control.hdl import *

class CounterModule(Module):
    def __init__(self, clock, start, stop, display):
        super().__init__(clock)
        self.start = inp(start)
        self.stop = inp(stop)
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
        if self.running:
            if self.counter == 15:
                self.counter <= 0
            else:
                self.counter <= int(self.counter) + 1
                
        self.display <= self.counter

        
clock = Clock(Hz=1)

counter = CounterModule(
    clock,
    start = start_btn,
    stop = stop_btn,
    display = display
)

clock.start()
```
Here the `@always` decorator and the `<=` operator are abused to mimic the Verilog syntax. Do not mind these too much for now.

This is a direct mapping from a corresponding Verilog code (if it were implemented in FPGA):
```verilog
module Counter(clock, start, stop, display);
    input clock;
    input reg start;
    input reg stop;
    output reg[3:0] display;

    reg[3:0] counter;
    reg running;

    always @(posedge clock) begin
        if (stop) begin
            running <= 1'b0;
        end
        else if (start) begin
            running <= 1'b1;
        end
    end

    always @(posedge clock) begin
        if (running) begin
            if (counter == 15) begin
                counter <= 0;
            end
            else begin
                counter <= counter + 1;
            end
        end
        display <= counter;
    end
endmodule

```
In SlowPy HDL, module arguments are all registers (except for the clock). Register initializations, typically done with RESET in FPGA, can be done in the `__init__()` function.

SlowPy HDL behaves like HDL. The following code works as if it were written in Verilog:
```python
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
```
Here the contents of the variables `self.a` and `self.b` are swapped on every clock cycle, in contrast to the software-like behavior where the contents of both the variables become 'B'.
