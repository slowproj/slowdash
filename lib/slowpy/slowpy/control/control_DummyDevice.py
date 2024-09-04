
import slowpy.control


class RandomWalkDeviceNode(slowpy.control.ControlNode):
    def __init__(self, walk, decay):
        self.device = slowpy.control.RandomWalkDevice(n=4, walk=walk, decay=decay, tick=0)
        
    ## child nodes ##
    # randomwalk_device().ch(0)
    def ch(self, channel):
        return RandomWalkChannelNode(self.device, channel)
            
    
    # randomwalk_device().walk()
    def walk(self):
        return RandomWalkConfigNode(self.device, 'walk')
            
    
    # randomwalk_device().decay()
    def decay(self):
        return RandomWalkConfigNode(self.device, 'decay')
            
    
    @classmethod
    def _node_creator_method(cls):
        def randomwalk_device(self, walk=1.0, decay=0.1):
            try:
                self.randomwalk_device_node.get()
            except:
                self.randomwalk_device_node = RandomWalkDeviceNode(walk=walk, decay=decay)

            return self.randomwalk_device_node

        return randomwalk_device


    
class RandomWalkChannelNode(slowpy.control.ControlValueNode):
    def __init__(self, device, channel):
        self.device = device
        self.channel = channel

        
    def set(self, value):
        self.device.write(self.channel, float(value))

        
    def get(self):
        return self.device.read(self.channel)


    
class RandomWalkConfigNode(slowpy.control.ControlValueNode):
    def __init__(self, device, param_name):
        self.device = device
        self.param_name = param_name

        
    def set(self, value):
        setattr(self.device, self.param_name, value)

        
    def get(self):
        return getattr(self.device, self.param_name)
