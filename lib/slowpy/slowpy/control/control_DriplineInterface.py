# Created by Sanshiro Enomoto on 27 May 2024 #


import slowpy.control as spc


class DriplineNode(spc.ControlNode):
    def __init__(self, *dl_args, **dl_kwargs):
        import dripline
        self.interface = dripline.core.Interface(*dl_args, **dl_kwargs)
        
    ## child nodes ##
    # dripline().endpoint(name)
    def endpoint(self, name):
        return DriplineEndpointNode(self.interface, name)
    
    @classmethod
    def _node_creator_method(cls):
        def dripline(self, *dl_args, **dl_kwargs):
            try:
                self.dripline_node
            except:
                self.dripline_node = DriplineNode(*dl_args, **dl_kwargs)

            return self.dripline_node

        return dripline

    
    
class DriplineEndpointNode(spc.ControlVariableNode):
    def __init__(self, interface, name):
        self.interface = interface
        self.name = name
            
    def set(self, value):
        self.interface.set(self.name, value)
    
    def get(self):
        return self.interface.get(self.name).payload.to_python().get('value_raw', None)

    def do_cmd(self, method, ordered_args=[], keyed_args={}, timeout=0):
        return self.interface.cmd(self.name, method, ordered_args, keyed_args, timeout)

    ## child nodes ##
    # dripline().endpoint(name).calibrated() 
    def calibrated(self):
        return DriplineCalibratedValueNode(self.interface, self.name)
    

    
class DriplineCalibratedValueNode(spc.ControlVariableNode):
    def __init__(self, interface, name):
        self.interface = interface
        self.name = name
            
    def set(self, value):
        self.interface.set(self.name, value)
    
    def get(self):
        return self.interface.get(self.name).payload.to_python().get('value_cal', None)
