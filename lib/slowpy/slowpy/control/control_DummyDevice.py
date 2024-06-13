
from slowpy.control import ControlNode, DummyDevice_RandomWalk



class DummyDeviceNode(ControlNode):
    def __init__(self, center, walk, decay):
        self.device = DummyDevice_RandomWalk(n=4, center=center, walk=walk, decay=decay, tick=0)
        
    ## child nodes ##
    # dummy_device().ch(0)
    def ch(self, channel):
        try:
            self.channel_nodes.keys()
        except:
            self.channel_nodes = {}
        if channel not in self.channel_nodes:
            self.channel_nodes[channel] = DummyDeviceChannelNode(self.device, channel)
            
        return self.channel_nodes[channel]
            
    
    @classmethod
    def _node_creator_method(cls):
        def dummy_device(self, center=0, walk=1.0, decay=0.1):
            try:
                self.dummy_node.get()
            except:
                self.dummy_node = DummyDeviceNode(center=center, walk=walk, decay=decay)

            return self.dummy_node

        return dummy_device

    
    
class DummyDeviceChannelNode(ControlNode):
    def __init__(self, device, channel):
        self.device = device
        self.channel = channel
            
    def set(self, value):
        self.device.write(self.channel, float(value))
    
    def get(self):
        return self.device.read(self.channel)



    
def export():
    return [ DummyDeviceNode ]
