
from slowpy import ControlNode, DummyDevice_RandomWalk



class DummyDeviceNode(ControlNode):
    def __init__(self, walk, decay):
        self.device = DummyDevice_RandomWalk(n=4, walk=walk, decay=decay, tick=0)
        
    ## child nodes ##
    # dummy_device().ch(0)
    def ch(self, channel):
        return DummyDeviceChannelNode(self.device, channel)
    
    @classmethod
    def _node_creator_method(cls):
        def dummy_device(self, walk=1.0, decay=0.1):
            try:
                self.dummy_node.get()
            except:
                self.dummy_node = DummyDeviceNode(walk=walk, decay=decay)

            return self.dummy_node

        return dummy_device

    
    
class DummyDeviceChannelNode(ControlNode):
    def __init__(self, device, channel):
        self.device = device
        self.channel = channel
            
    def set(self, value):
        self.device.write(self.channel, value)
    
    def get(self):
        return self.device.read(self.channel)



    
def export():
    return [ DummyDeviceNode ]
