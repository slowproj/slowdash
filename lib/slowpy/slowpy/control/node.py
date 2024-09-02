import os, time, threading, importlib, logging, traceback


class ControlNode:
    # override this
    def set(self, value):
        return None

    # override this
    def get(self):
        return None

    # override this
    def has_data(self):
        return None

    
    # stoppable-sleep: to be used in subclasses
    def sleep(self, duration_sec):
        sec10 = int(10*duration_sec)
        subsec10 = 10*duration_sec - sec10
        if sec10 > 0:
            for i in range(sec10):
                if self.is_stop_requested():
                    return False
                else:
                    time.sleep(0.1)
        elif subsec10 > 0:
            time.sleep(subsec/10.0)

        return not self.is_stop_requested()

    
    # stoppable-wait: to be used in subclasses
    # condition_lambda is a function that takes a value from self.get() and returns True or False.
    #   example: lambda x: (float(x)>100)
    def wait_until(condition_lambda, poll_interval=0.1, timeout=0):
        while True:
            if self.has_data() is not False and condition_lambda(self.get()):
                return True
            if not self.is_stop_requested():
                return False
            if timeout > 0 and (time.time() - start > timeout):
                return False
            time.sleep(poll_interval)
            
        return False
        
            
    # to be used by external code
    def __call__(self, value=None):
        if value is not None:
            return self.set(value)
        else:
            return self.get()
    
    def __repr__(self):
        return repr(self.get())
    
    def __str__(self):
        return str(self.get())
    
    def __bool__(self):
        return bool(self.get())
    
    def __int__(self):
        return int(self.get())
    
    def __float__(self):
        value = self.get()
        try:
            return float(value)
        except:
            return float("nan")

    
    # override this to add a child endoint
    @classmethod
    def _node_creator_method(MyClass):    # return a method to be injected
        def child(self, *args, **kwargs):  # "self" here is a parent (the node to which this method is added)
            return MyClass(*args, **kwargs)
        return child

    
    @classmethod
    def add_node(cls, NodeClass, name=None):
        method = NodeClass._node_creator_method()
        if name is None:
            name = method.__name__
        setattr(cls, name, method)

        
    @classmethod
    def import_control_module(cls, module_name, search_dirs=[]):
        filename = 'control_%s.py' % module_name
        this_search_dirs = search_dirs + [
            os.path.abspath(os.getcwd()),
            os.path.abspath(os.path.dirname(__file__))
        ]
        for module_dir in this_search_dirs:
            filepath = os.path.join(module_dir, filename)
            if os.path.isfile(filepath):
                break
        else:
            logging.error('unable to find control plugin: %s' % module_name)
            return cls
        
        try:
            module = importlib.machinery.SourceFileLoader(filename, filepath).load_module()
        except Exception as e:
            logging.error('unable to load control module: %s: %s' % (module_name, str(e)))
            logging.error(traceback.format_exc())
            return cls
        
        logging.info('loaded control module "%s"' % module_name)

        export_func = module.__dict__.get('export', None)
        if export_func is not None:
            for func in export_func():
                cls.add_node(func)
        else:
            node_classes = []
            for name, entry in module.__dict__.items():
                if callable(entry):
                    if '_node_creator_method' in dir(entry):
                        node_classes.append(entry)
            if len(node_classes) > 1:
                cls.add_node(node_classes[1])
            else:
                logging.error('unable to identify Node class: %s' % module_name)
                
        return cls

        
    _global_stop_event = threading.Event()
    def is_stop_requested(self):
        if self._global_stop_event.is_set():
            return True
        if hasattr(self, 'node_thread_stop_event') and self.node_thread_stop_event.is_set():
            return True
        return False


    
class ControlThreadNode(ControlNode):
    def __init__(self):
        super().__init__()
        self.node_thread = None
        self.node_thread_stop_event = threading.Event()

        
    # if "self" has the "run()" and/or "loop()" methods, "start()" will create a thread and call it
    def start(self):
        if not (callable(getattr(self, 'run', None)) or callable(getattr(self, 'loop', None))):
            return

        if self.node_thread is not None:
            # already running
            return
        
        self.node_thread = NodeThread(self)
        self.node_thread_stop_event.clear()
        self.node_thread.start()
            

    def stop(self):
        if self.node_thread is None:
            return
        
        self.node_thread_stop_event.set()
        self.node_thread.join()
        self.node_thread = None
        
        
        
class NodeThread(threading.Thread):
    def __init__(self, node):
        threading.Thread.__init__(self)
        self.node = node

    def run(self):
        if callable(getattr(self.node, 'run', None)):
            self.node.run()
            
        if callable(getattr(self.node, 'loop', None)):
            while not self.node.is_stop_requested():
                self.node.loop()
            
    

class ControlValueNode(ControlNode):
    def __init__(self):
        super().__init__()
    

    ### child nodes ###
    # hold setpoint
    def setpoint(self):
        try:
            self._node_setpoint.get()
        except:
            self._node_setpoint = SetpointNode(self)
        return self._node_setpoint

    
    # ramp the set value
    def ramping(self, change_per_sec=None):
        try:
            self._node_ramping.get()
            if change_per_sec is not None:
                self._node_ramping.change_per_sec = abs(float(change_per_sec))
        except:
            self._node_ramping = RampingNode(self, change_per_sec)
        return self._node_ramping
    

    
class SetpointNode(ControlNode):
    def __init__(self, node):
        self.node = node
        self.setpoint = None

        
    def set(self, value):
        self.setpoint = value
        self.node.set(value)

        
    def get(self):
        return self.setpoint

    
        
class RampingNode(ControlNode):
    def __init__(self, value_node, change_per_sec):
        self.value_node = value_node
        self.change_per_sec = None
        try:
            if float(change_per_sec) > 0:
                self.change_per_sec = float(change_per_sec)
        except:
            self.change_per_sec = None
                
        self.target_value = None

        
    def set(self, target_value):
        if self.change_per_sec is None or (self.change_per_sec < 1e-10):
            self.value_node.setpoint().set(target_value)
            return
        
        self.target_value = float(target_value)
        try:
            current_value = float(self.value_node.get())
        except:
            try:
                current_value = float(self.value_node.setpoint().get())
            except:
                return
        tolerance =  1e-5 * (abs(self.target_value) + abs(current_value) + 1e-10)
        
        while self.target_value is not None:
            diff = current_value - self.target_value
            if abs(diff) < tolerance:
                break
            elif abs(diff) <= self.change_per_sec:
                current_value = self.target_value
            elif diff > 0:
                current_value -= self.change_per_sec
            else:
                current_value += self.change_per_sec
            self.value_node.setpoint().set(current_value)

            for i in range(10):
                if self.is_stop_requested():
                    self.target_value = None
                    return
                else:
                    time.sleep(0.1)
            
        self.target_value = None


    def get(self):
        return self.value_node.get() if self.target_value is None else self.target_value


    # child nodes
    def status(self):
        return RampingStatusNode(self)

    
        
class RampingStatusNode(ControlNode):
    def __init__(self, ramping_node):
        self.ramping_node = ramping_node

        
    def set(self, zero_to_stop):
        if str(zero_to_stop) == '0':
            self.ramping_node.target_value = None

    
    def get(self):
        return self.ramping_node.target_value is not None
    
