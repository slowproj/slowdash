# Created by Sanshiro Enomoto on 7 September 2024 #


import time, threading, inspect
import slowpy.control as spc


class RegisterNode(spc.ControlNode):
    '''Implements the HDL Register behavior, combined with the Clock class below
    - `set()` to this register will take effect (calling `set()` of the attached node) on the next clock cycle
    - `get()` from this register will return a value latched on the previous clock cycle
    - The Clock class calls `set()` of all the registers then `get()` periodically at a specified interval
    - An alias operator `<=` is added for calling `set()`
    - To use the `<=` operator for the usual way (numerical comparison), do like `float(reg) <= 31`.
    '''
    
    def __init__(self, node=None):
        self.node = node
        self.set_value = None
        self.get_value = None
        self.has_input = False
        self.has_output = False

        
    def set(self, value):
        if self.set_value is not None:
            raise spc.ControlException('setting a register value from multiple sources')
        self.set_value = value

        
    def get(self):
        return self.get_value


    def _update_output(self):
        if self.set_value is None:
            return

        if self.node is not None and self.has_output:
            self.node.set(self.set_value)
        
        if self.node is None or not self.has_input:
            self.get_value = self.set_value
            
        self.set_value = None

            
    def _update_input(self):
        if self.node is not None and self.has_input:
            self.get_value = self.node.get()
        else:
            pass  # already taken care of in _update_output()


            
def reg(node=None):
    if node is None:
        return RegisterNode()
    
    try:
        node._register_node.get()
    except:
        node._register_node = RegisterNode(node)

    return node._register_node


def input_reg(node):
    register = reg(node)
    register.has_input = True
    return register


def output_reg(node):
    register = reg(node)
    register.has_output = True
    return register


def inout_reg(node):
    register = reg(node)
    register.has_input = True
    register.has_output = True
    return register



class Clock(threading.Thread):
    def __init__(self, Hz=1):
        threading.Thread.__init__(self)
        self.stop_event = threading.Event()
        
        self.interval = 1.0/Hz
        self.modules = []

        self.processes = []
        self.registers = []

        self.start_time = None
        self.ticks = 0
        
        
    def add_module(self, module):
        self.modules.append(module)

        
    def initialize(self, params={}):
        for module in self.modules:
            for name, member in inspect.getmembers(module, inspect.ismethod):
                if str(inspect.signature(member)) == str(inspect.signature(always(None))):
                    #print(f'HDL.always: {type(module).__name__}.{name}')
                    self.processes.append(member)
                
            for item_name in vars(module):
                item = getattr(module, item_name)
                if isinstance(item, RegisterNode):
                    self.registers.append(item)

        # initial values might have been set
        for reg in self.registers:
            reg._update_output()

        self.start_time = time.time()
        self.next_time = self.start_time
        self.ticks = 0

        
    # loop option: call this in a loop
    def loop(self):
        if self.start_time is None:
            self.initialize()
            
        now = time.time()
        if self.next_time < now:
            self.ticks = int((now - self.start_time) / self.interval) + 1
            self.next_time = self.start_time + self.ticks * self.interval

            for reg in self.registers:
                reg._update_input()
            for proc in self.processes:
                proc()
            for reg in self.registers:
                reg._update_output()

        elif self.next_time - now < 2:
            time.sleep(self.next_time - now < 2)
        else:
            time.sleep(1)

            
    # threading option: use start() to start, stop() to stop
    def run(self):
        self.stop_event.clear()
        while not self.stop_event.is_set() and not spc.ControlSystem.is_stop_requested():
            self.loop()
                

    # for threading option
    def stop(self):
        self.stop_event.set()

            

            
class Module:
    def __init__(self, clock):
        clock.add_module(self)


        
# decorator to identify the process methods
def always(func):
    def wrapper(*_slowpy_always_args, **_slowpy_always_kwargs):
        return func(*_slowpy_always_args, **_slowpy_always_kwargs)
    return wrapper
