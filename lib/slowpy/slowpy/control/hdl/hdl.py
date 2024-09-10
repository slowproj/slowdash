# Created by Sanshiro Enomoto on 7 September 2024 #


import time, threading, inspect
import slowpy.control as spc


class RegisterNode(spc.ControlNode):
    '''Implements the HDL Register behavior, combined with the Clock class below
    - `set()` to this register will take effect (calling `set()` of the attached node) on the next clock cycle
    - `get()` from this register will return a value latched on the previous clock cycle
    - The Clock class calls `set()` of all the registers then `get()` periodically at a specified interval
    - An alias operator `<=` is added for calling `set()`
    - To use the `<=` operator for the usual way, do like `float(reg) <= 31`.
    '''
    
    def __init__(self, node=None):
        self.node = node
        self.set_value = None
        self.get_value = None
        self.has_input = False
        self.has_output = False

        
    def __le__(self, value):
        if isinstance(value, spc.ControlNode):
            return self.set(value.get())
        else:
            return self.set(value)

        
    def set(self, value):
        if self.set_value is not None:
            raise spc.ControlException('setting a register value from multiple sources')
        self.set_value = value

        
    def get(self):
        return self.get_value


    def _update_output(self):
        if self.set_value is None:
            return
        
        if self.node is None:
            self.get_value = self.set_value
        else:
            self.node.set(self.set_value)
        self.set_value = None

            
    def _update_input(self):
        if self.node is None:
            pass  # already taken care of in _update_output()
        else:
            self.get_value = self.node.get()


            
def reg(node=None):
    if node is None:
        return RegisterNode()
    
    try:
        node._register_node.get()
    except:
        node._register_node = RegisterNode(node)

    return node._register_node


def inp(node):
    register = reg(node)
    register.has_input = True
    return register


def outp(node):
    register = reg(node)
    register.has_output = True
    return register



class Clock(threading.Thread):
    def __init__(self, Hz=1):
        threading.Thread.__init__(self)
        self.stop_event = threading.Event()
        
        self.interval = 1.0/Hz
        self.modules = []

        
    def add_module(self, module):
        self.modules.append(module)

        
    def stop(self):
        self.stop_event.set()

            
    def run(self):
        processes = []
        input_registers, output_registers = [], []
        for module in self.modules:
            for name, member in inspect.getmembers(module, inspect.ismethod):
                if str(inspect.signature(member)) == str(inspect.signature(always(None))):
                    #print(f'HDL.always: {type(module).__name__}.{name}')
                    processes.append(member)
                
            for item_name in vars(module):
                item = getattr(module, item_name)
                if isinstance(item, RegisterNode):
                    if item.has_input or not item.has_output:
                        input_registers.append(item)
                    if item.has_output or not item.has_input:
                        output_registers.append(item)

        # initial values might have been set
        for reg in output_registers:
            reg._update_output()
            
        start_time = time.time()
        ticks = 0
        while not self.stop_event.is_set() and not spc.ControlSystem.is_stop_requested():
            for reg in input_registers:
                reg._update_input()

            for proc in processes:
                proc()
                
            for reg in output_registers:
                reg._update_output()

            ticks += 1
            now = time.time()
            togo = (start_time + ticks * self.interval) - now
            if togo <= 0:
                ticks = int((now - start_time) / self.interval)
            else:
                time.sleep(togo)
                

            
class Module:
    def __init__(self, clock):
        clock.add_module(self)


        
# decorator to identify the process methods
def always(func):
    def wrapper(*_slowpy_always_args, **_slowpy_always_kwargs):
        return func(*_slowpy_always_args, **_slowpy_always_kwargs)
    return wrapper
