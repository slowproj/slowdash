# Created by Sanshiro Enomoto on 7 September 2024 #


import time, threading, inspect
import slowpy.control as spc


class RegisterNode(spc.ControlNode):
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


            
def register(node=None):
    if node is None:
        return RegisterNode()
    
    try:
        node._register_node.get()
    except:
        node._register_node = RegisterNode(node)

    return node._register_node


def inp(node):
    reg = register(node)
    reg.has_input = True
    return reg


def outp(node):
    reg = register(node)
    reg.has_output = True
    return reg



class Clock(threading.Thread):
    def __init__(self, Hz=1):
        threading.Thread.__init__(self)
        self.interval = 1.0/Hz
        self.modules = []

        
    def add_module(self, module):
        self.modules.append(module)
        

    def run(self):
        processes = []
        input_registers, output_registers = [], []
        for module in self.modules:
            for name, member in inspect.getmembers(module, inspect.ismethod):
                if str(inspect.signature(member)) == str(inspect.signature(always(None))):
                    print(f'HDL.always: {type(module).__name__}.{name}')
                    processes.append(member)
                
            for item_name in vars(module):
                item = getattr(module, item_name)
                if isinstance(item, RegisterNode):
                    if item.has_input or not item.has_output:
                        input_registers.append(item)
                    if item.has_output or not item.has_input:
                        output_registers.append(item)
                        
        start_time = time.time()
        ticks = 0
        while True:
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


# decorator to attach "is_process" attribute
def always(func):
    def wrapper(*_always_args, **_always_kwargs):
        return func(*_always_args, **_always_kwargs)
    return wrapper


    
################


class ValueNode(spc.ControlNode):
    def __init__(self, initial_value=None):
        self.value = initial_value

    def set(self, value):
        self.value = value

    def get(self):
        return self.value

    @classmethod
    def _node_creator_method(cls):
        def value(self, initial_value=None):
            return ValueNode(initial_value)
        return value

    
class OneshotNode(spc.ControlNode):
    def __init__(self, node, duration=None, normal=None):
        '''
        Args:
            duration (float or None): if None, the first get() after set() returns the set-value
        '''
        self.node = node
        self.duration = abs(float(duration)) if duration is not None else None
        self.normal = normal
        
        self.start_time = None
        
    def set(self, value):
        if self.normal is None:
            self.normal = self.node.get()
        self.node.set(value)
        self.start_time = time.time()

    def get(self):
        if self.start_time is not None:
            if self.duration is None:
                value = self.node.get()
                self.node.set(self.normal)
                self.start_time = None
                return value
                
            if time.time() > self.start_time + self.duration:
                self.node.set(self.normal)
                self.start_time = None
                
        return self.node.get()

    @classmethod
    def _node_creator_method(cls):
        def oneshot(self):
            return OneshotNode(self)
        return oneshot

    
spc.ControlSystem.add_node(ValueNode)
spc.ControlSystem.add_node(OneshotNode)


################


ctrl = spc.ControlSystem()
ValueNode.add_node(OneshotNode)
print("ControlNodeMethods: ", [n for n, member in inspect.getmembers(ctrl, inspect.ismethod)])
print("ValueNodeMethods: ", [n for n, member in inspect.getmembers(ValueNode, inspect.ismethod)])
start_btn = ctrl.value(False).oneshot()
stop_btn = ctrl.value(False).oneshot()
display = ctrl.value()

def _export():
    return [
        ('start', start_btn.writeonly()),
        ('stop', stop_btn.writeonly()),
        ('display', display.readonly())
    ]



class CounterModule(Module):
    def __init__(self, clock, start, stop, display):
        super().__init__(clock)
        
        self.start = inp(start)
        self.stop = inp(stop)
        self.display = outp(display)
        self.counter = register()
        self.running = register()

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

    @always
    def show_internals(self):
        print(self.start, self.stop, self.counter)

        


clock = Clock(Hz=1)
counter = CounterModule(
    clock,
    start = start_btn,
    stop = stop_btn,
    display = display
)
clock.start()


time.sleep(3)
start_btn.set(True)
time.sleep(5)
stop_btn.set(True)
time.sleep(5)
start_btn.set(True)
