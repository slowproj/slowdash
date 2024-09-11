---
title: "SlowPy HDL (experimental)"
---


# Overview
SlowPy HDL enables describing control sequences in a Verilog-like style. If you are not familiar with Hardware Description Languages (HDL) such as VHDL and Verilog, you will be confused and will hate this. Please do not use this feature in that case. Some people, however, might find this a straightforward way to build parallel concurrent state machines. This feature was originally designed to replace legacy PLC (Programmable Logic Controller) systems with SlowPy; ladder logic can be directly translated to SlowPy HDL processes.


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

The logic to control the counter can be written like this:
```python
from slowpy.control.hdl import *

class CounterModule(Module):
    def __init__(self, clock, start, stop, counter):
        super().__init__(clock)
        self.start = inp(start)
        self.stop = inp(stop)
        self.counter = outp(counter)
        self.running = reg()

        self.running <= False
        self.counter <= 0
                
    @always
    def startstop(self):
        if self.stop:
            self.running <= False
        elif self.start:
            self.running <= True

    @always
    def count(self):
        if self.running:
            if self.counter == 10:
                self.counter <= 0
            else:
                self.counter <= int(self.counter) + 1

        
clock = Clock(Hz=1)

counter = CounterModule(
    clock,
    start = start_btn,
    stop = stop_btn,
    counter = display
)

clock.start()
```
Here the `@always` decorator and the `<=` operator are abused to mimic the Verilog syntax. Do not mind these too much for now.

This is a direct mapping from a corresponding Verilog code (if it were implemented in FPGA):
```verilog
module Counter(clock, start, stop, counter);
    input clock;
    input reg start;
    input reg stop;
    output reg[3:0] counter;
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
        if (running == 1'b1)
            if (counter == 4'ha)
                counter <= 4'h0;
            else
                counter <= counter + 4'h1;
    end
endmodule

```
In SlowPy HDL, module arguments are all registers (except for the clock). Register initializations, typically done with RESET in FPGA, can be done in the `__init__()` function.

SlowPy HDL behaves like HDL. The following code works as if it were written in Verilog:
```python
class TestModule(Module):
    def __init__(self, clock, a, b):
        super().__init__(clock)
        self.a = reg(a)
        self.b = reg(b)
        
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
class UserModule(Module):
    def __init__(self, clock, var1, var2, ...):
        # clock binding (base class initialization)
        super().__init__(clock)
        
        # registers and input/output binding
        self.var1 = inp(var1)    # register for input
        self.var2 = outp(var2)   # register for output
        self.var3 = reg()        # internal register
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
module = UserModule(clock, var1=node1, var2=node2, ...)


# starting the thread
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


### Registers
This implements the flip-flop behavior. The value of a register is updated on clock cycles. If the register is bound to a input from a node (by `register = inp(node)`), the `get()` of the node is called before the clock cycle and held until next cycle. If the register is bound to an output to a node (by `register = outp(node)`, the assigned value is written to the node only once right after a clock cycle. If it is not bound to a node, the assigned value will take effect on the next clock cycle.

Register value assignment should be done with a special operator `<=`. The usual assignment operator, `=`, works in the same way, but using `<=` highlights this semantics. Also using the `<=` operator to a non-register object should cause a syntax error, helping detect this hard-to-notice error.

To use the `<=` operator in the usual way (numeric comparison), do like `int(reg) < 32`.

The content of the register is just a Python value, therefore any Python value types can be stored, not limited to numerical types.


# Internal Implementation
#### Structure
- When the `Module` class is initialized with a clock, it registers itself to the clock object, so that the clock object knows all the modules under its control.

- The clock object scans the module contents, for
  - the register members, by `isinstance(member, Register)`, and
  - the process methods, by looking for the `@always` decorator signature.
  
- Each register has two internal values, one for reading and one for writing, in addition to the bound node.
  - Reading from a register returns the reading value.
  - The overloaded `register <= rhs` operator sets the rhs value to the register writing value.

#### Node-Register Binding
- The `inp(node)`/`outp(node)` functions create a register bound to the node and mark it for reading/writing.
- The `reg(node)` functions creates a register bound to the node and marks it for both reading and writing.
- The `reg()` functions creates a register not bound to any nodes.
<p>
- Using the `<=` operator directly to a node should cause a syntax error.
- Using the `=` operator directly to a node is still possible, and the assignment will take effect immediately, but doing it is not recommended.

#### Sequence
- A clocking thread is started by `Clock.start()`. In the thread, the clock object repeatedly performs:
  1. For all the input registers, call `get()` of the bound nodes and set it to the register reading value
  2. Call all the process methods
  3. For all the output registers, call `set()` of the bound nodes with the register writing value
  4. For all the internal registers, copy the writing value to reading value
  5. Sleep until the next clock cycle
  