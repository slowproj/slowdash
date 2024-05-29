import os, time, importlib, logging, traceback


class ControlNode:
    # override this
    def set(self, value):
        pass

    # override this
    def get(self):
        return None

    # override this
    def has_data(self):
        return None

    def __str__(self):
        return str(self.get())
    
    def __float__(self):
        return float(self.get())


    # child nodes
    def ramp(self, change_per_sec=None):
        try:
            self.ramp_node.get()
            if change_per_sec is not None:
                self.ramp_node.change_per_sec = abs(float(change_per_sec))
        except:
            self.ramp_node = RampNode(self, change_per_sec)
        return self.ramp_node
    

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

    def load_control_module(cls, module_name, search_dirs=[]):
        filename = 'control_%s.py' % module_name
        if search_dirs is None or len(search_dirs) == 0:
            search_dirs = [
                os.path.abspath(os.getcwd()),
                os.path.abspath(os.path.dirname(__file__))
            ]
        for module_dir in search_dirs:
            filepath = os.path.join(module_dir, filename)
            if os.path.isfile(filepath):
                break
        else:
            logging.error('unable to find control plugin: %s' % module_name)
            return None
        
        try:
            module = importlib.machinery.SourceFileLoader(filename, filepath).load_module()
        except Exception as e:
            logging.error('unable to load control module: %s: %s' % (module_name, str(e)))
            logging.error(traceback.format_exc())
            return None
        
        logging.debug('loaded control module "%s"' % module_name)

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

        

class RampNode(ControlNode):
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
            self.value_node.set(target_value)
            return
            
        self.target_value = float(target_value)
        current_value = float(self.value_node.get())
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
            self.value_node.set(current_value)
            time.sleep(1)
            
        self.target_value = None


    def get(self):
        return self.value_node.get()


    # child nodes
    def status(self):
        return RampStatusNode(self)

    
        
class RampStatusNode(ControlNode):
    def __init__(self, ramp_node):
        self.ramp_node = ramp_node

        
    def set(self, zero_to_stop):
        if str(zero_to_stop) == '0':
            self.ramp_node.target_value = None

    
    def get(self):
        return self.ramp_node.target_value is not None
    
    
    
class ControlSystem(ControlNode):
    def __init__(self):
        self.load_control_module('Ethernet')
