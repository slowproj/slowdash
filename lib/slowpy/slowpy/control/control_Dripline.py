
import time, logging
from slowpy.control import ControlNode


class DriplineNode(ControlNode):
    def __init__(self, dripline_config):
        import dripline
        self.interface = dripline.core.Interface(dripline_config)
        
    ## child nodes ##
    # dripline().endpoint(name)
    def endpoint(self, name):
        return DriplineEndpointNode(self.interface, name)
    
    @classmethod
    def _node_creator_method(cls):
        def dripline(self, dripline_config={}):
            try:
                self.dripline_node.get()
            except:
                self.dripline_node = DriplineNode(dripline_config)

            return self.dripline_node

        return dripline

    
    
class DriplineEndpointNode(ControlNode):
    def __init__(self, interface, name):
        self.interface = interface
        self.name = name
            
    def set(self, value):
        self.interface.set(self.name, value)
    
    def get(self):
        return self.interface.get(self.name).payload.to_python().get('value_raw', None)

    def cmd(self, method, ordered_args=[], keyed_args={}, timeout=0):
        return self.interface.cmd(self.name, method, ordered_args, keyed_args, timeout)

    ## child nodes ##
    # dripline().endpoint(name).calibrated() 
    def calibrated(self):
        return DriplineCalibratedValueNode(self.interface, self.name)
    

    
class DriplineCalibratedValueNode(ControlNode):
    def __init__(self, interface, name):
        self.interface = interface
        self.name = name
            
    def set(self, value):
        self.interface.set(self.name, value)
    
    def get(self):
        return self.interface.get(self.name).payload.to_python().get('value_cal', None)


    
def export():
    return [ DriplineNode ]
