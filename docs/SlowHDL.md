---
title: "SlowPy HDL (experimental)"
---


# Overview
SlowPy HDL enables describing control sequences in a Verilog-like style. If you are not familiar with Hardware Description Languages (HDL) such as VHDL and Verilog, you will be confused and will hate this. Please do not use this feature in that case. Some people, however, might find this a straightforward way to build parallel concurrent state machines. This feature was originally designed to replace legacy PLC (Programmable Logic Controller) systems with SlowPy; ladder logic can be directly translated to SlowPy HDL processes.


### Example
For a control system that consists of a counter display and start / stop / clear buttons:
```python
import slowpy.control as spc

ctrl = spc.ControlSystem()    
start_btn = ctrl.value(initial_value=False).oneshot()
stop_btn = ctrl.value(initial_value=False).oneshot()
clear_btn = ctrl.value(initial_value=False).oneshot()
display = ctrl.value()

def _export():
    return [
        ('start', start_btn.writeonly()),
        ('stop', stop_btn.writeonly()),
        ('clear', clear_btn.writeonly()),
        ('display', display.readonly())
    ]
```

We will make a counter with start/stop/clear, the value of which is shown in the display.

If this were to be implemented in FPGA, a Verilog code block (excluding RESET) would look like:
```verilog
module Counter(clock, start, stop, clear, count);
    input clock;
    input start;
    input stop;
    input clear;
    output reg[7:0] count;
    reg running;

    always @(posedge clock) 
    begin
        if (stop == 1'b1)
            running <= 1'b0;
        else if (start == 1'b1)
            running <= 1'b1;
    end

    always @(posedge clock) 
    begin
        if (clear == 1'b1)
            count <= 8'd0;
        else if (running == 1'b1)
            if (count == 8'd59)
                count <= 8'd0;
            else
                count <= count + 8'd1;
    end
endmodule
```

The SlowPy-HDL code (Python software script; emulation of HDL behavior) has basically the same structure:
```python
from slowpy.control.hdl import *

# control module, with inputs and outputs given in the __init()__ arguments
class CounterModule(Module):
    def __init__(self, clock, start, stop, clear, count):
        super().__init__(clock)

        # internal registers and binding of inputs and outputs
        self.start = input_reg(start)
        self.stop = input_reg(stop)
        self.clear = input_reg(clear)
        self.count = output_reg(count)
        self.running = reg()

        # initialization (RESET)
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
            if self.count == 59:
                self.count <= 0
            else:
                self.count <= int(self.count) + 1


# Create an instance, map peripherals (SlowPy control nodes)

clock = Clock(Hz=1)

counter = CounterModule(
    clock,
    start = start_btn,
    stop = stop_btn,
    clear = clear_btn,
    count = display
)

clock.start()
```
Here the `@always` decorator and the `<=` operator are abused to mimic the Verilog syntax. In SlowPy HDL, module arguments are all registers (except for the clock). Register initializations, typically done with RESET in FPGA, can be done in the `__init__()` function.

SlowPy HDL behaves like HDL. The following code works as if it were written in Verilog:
```python
class TestModule(Module):
    def __init__(self, clock, a, b):
        super().__init__(clock)
        self.a = output_reg(a)
        self.b = output_reg(b)
        
        self.a <= 'A'
        self.b <= 'B'
        
    @always
    def swap_ab(self):
        self.a <= self.b
        self.b <= self.a
```
Here the contents of the variables `self.a` and `self.b` are swapped on every clock cycle, in contrast to the software-like behavior where the contents of both the variables become 'B'.


# Construct

## Typical Code Structure
```python

# SlowPy Control Nodes to control (external devices etc.)
from slowpy.control import ControlSystem
ctrl = ControlSystem()
node1 = ctrl.whatever()....
node2 = ctrl.whatever()....
...

from slowpy.control.hdl import *

# user class to implement the logic
class MyModule(Module):
    def __init__(self, clock, var1, var2, ...):
        # clock binding (base class initialization)
        super().__init__(clock)
        
        # registers and input/output binding
        self.var1 = input_reg(var1)    # register for input
        self.var2 = output_reg(var2)   # register for output
        self.var3 = reg()              # internal register
        ...

        # initial values
        self.var2 <= 0
        self.var3 <= 0
        ...
        
    # recurrent process (called on every clock cycle)
    @always
    def process1(self):
        if int(self.var1) == 1:   # condition on register values
            self.var1 <= ...      # rhs: expression on register values, lhs: register to update
        else:
            self.var2 <= ...

    @always
    def process2(self):
        ...
        
        
# create instances
clock = Clock(Hz=1)
module = MyModule(clock, var1=node1, var2=node2, ...)


# starting the thread for standalone execution; for use in SlowTask, see below.
if __name__ == '__main__':
   clock.start()
```

## Behavior
- Module implements the user logic, and clock calls user methods recurrently in a dedicated thread.
- External control variables (SlowPy control nodes) are assigned to module's internal registers for input, output, or both.
- The methods in the module decorated with `@always` is called on every clock cycle.
- Register values are assigned with the `<=` operator. The assigned value takes effect on the next clock cycle.


## Components
### Modules
User modules must be derived from the `Module` class defined in `slowpy.control.hdl`. The constructor (`__init__()`) of the `Module` class takes an argument for an instance of the `Clock` class described below. The user class methods that are decorated with `@always` will be called on each clock cycle.


### Clock
A clock defines the recurrence intervals. An instance of the `Clock` class is passed to `Module` instances. Clocks create a own thread by `start()` for the recurrent calls of the module processes (the methods decorated with `@always`).

It is possible and maybe useful to create multiple clocks at different frequencies. For example, if a device is slow and readout from it takes time, a slow clock can be used to (pre)fetch the data from the device.

### Registers
This implements the flip-flop behavior. The value of a register is updated on clock cycles. If the register is bound to an input from a node (by `register = input_reg(node)` or `register = inout_reg(node)`), the `get()` of the bound node is called just before every clock cycle and the value is held until the next cycle. If the register is bound to an output to a node (by `register = output_reg(node)` or `register = inout_reg(node)`), the assigned register value is written to the node by callling `set(value)` right after every clock cycle. If a register is not bound to a node, the assigned value will take effect on the next clock cycle.

The `<=` operator is overloaded for register value assignment. To use the operator in the usual way (numeric comparison), do like `int(reg) <= 31`.

The content of a register is just a Python value, therefore any Python value types can be stored, not limited to numerical types.


# Using in SlowTask
Keep it in mind that each Clock instance has its own thread. Use SlowTask's `_run()` and `_halt()` to control the thread.

```python
#... Variable Nodes

class MyModule(Module):
#...

clock = Clock(Hz=1)
module = MyModule(
    clock,
    #...
)


# SlowTask callbacks

def _run():
    clock.start()   # start the clocking thread
    clock.join()    # wait for the thread to terminate

def _halt():
    clock.stop()    # stop the thread


# for standalone execution (not in SlowTask)
if __name__ == '__main__':
   clock.start()
```

Note that by the end of `_run()`, the thread must have been completed, otherwise the next start of SlowTask would duplicate the clocking thread.


# Internal Implementation
#### Structure
- When the `Module` class is initialized with a clock, it registers itself to the clock object, so that the clock object knows all the modules under its control.

- The clock object scans the module contents, for
  - the register members, by `isinstance(member, Register)`, and
  - the process methods, by looking for the `@always` decorator signature.
  
- Each register has two internal values, one for reading and one for writing, in addition to the bound node.
  - Reading from a register returns the reading value.
  - The overloaded operator `register <= rhs` sets the rhs value to the register writing value.

#### Node-Register Binding
- The `input_reg(node)` function creates a register bound to the node and mark it for reading.
- The `output_reg(node)` function creates a register bound to the node and mark it for writing. Reading from this register returns the value written on the last clock, instead of getting a value from the bound node.
- The `inout_reg(node)` function creates a register bound to the node and marks it for both reading and writing.
- The `reg()` function creates a register not bound to any nodes. Reading from it returns the value written on the last clock.

#### Sequence
- A clocking thread is started by `Clock.start()`. In the thread, the clock object repeatedly performs:
  1. For all the input registers, call `get()` of the bound nodes and set it to the register reading value
  2. Call all the process methods
  3. For all the output registers, call `set()` of the bound nodes with the register writing value
  4. For all the internal registers, copy the writing value to reading value
  5. Sleep until the next clock cycle
  