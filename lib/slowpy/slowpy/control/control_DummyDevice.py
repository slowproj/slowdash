# Created by Sanshiro Enomoto on 24 May 2024 #


import time
import slowpy.control as spc


class RandomWalkDeviceNode(spc.ControlNode):
    def __init__(self, walk, decay, n=4):
        self.device = spc.RandomWalkDevice(n=n, walk=walk, decay=decay, tick=0)
        self.ch_node = [ RandomWalkChannelNode(self.device, ch) for ch in range(n) ]
        self.walk_node = RandomWalkConfigNode(self.device, 'walk')
        self.decay_node = RandomWalkConfigNode(self.device, 'decay')
        
    ## child nodes ##
    # randomwalk_device().ch(0)
    def ch(self, channel):
        return self.ch_node[channel]
            
    
    # randomwalk_device().walk()
    def walk(self):
        return self.walk_node
            
    
    # randomwalk_device().decay()
    def decay(self):
        return self.decay_node
            
    
    @classmethod
    def _node_creator_method(cls):
        def randomwalk_device(self, walk=1.0, decay=0.1):
            try:
                self.randomwalk_device_node.get()
            except:
                self.randomwalk_device_node = RandomWalkDeviceNode(walk=walk, decay=decay)

            return self.randomwalk_device_node

        return randomwalk_device


    
class RandomWalkChannelNode(spc.ControlVariableNode):
    def __init__(self, device, channel):
        self.device = device
        self.channel = channel

        
    def set(self, value):
        self.device.write(self.channel, float(value))

        
    def get(self):
        return self.device.read(self.channel)


    
class RandomWalkConfigNode(spc.ControlVariableNode):
    def __init__(self, device, param_name):
        self.device = device
        self.param_name = param_name

        
    def set(self, value):
        setattr(self.device, self.param_name, value)

        
    def get(self):
        return getattr(self.device, self.param_name)



class RandomEventDeviceNode(spc.ControlNode):
    def __init__(self, n=16, rate=10, occupancy=0.5, t_mean=100, q_mean=100, q_sigma=10):
        self.n = n
        self.random_trigger_interval = spc.RandomIntervalDevice(n=1, interval=1.0/rate)
        self.random_hit = spc.RandomHitDevice(n=n, occupancy=occupancy)
        self.random_charge = spc.RandomChargeDevice(n=n, mean=q_mean, sigma=q_sigma)
        self.random_interval = spc.RandomIntervalDevice(n=n, interval=t_mean)
        

    def get(self):
        dt = self.random_trigger_interval.read(0)
        time.sleep(dt)

        event = {}
        hits = [ ch for ch in range(self.n) if self.random_hit.read(ch) ]
        for ch in hits:
            event[f'tdc{ch:02d}'] = int(self.random_interval.read(ch))
        for ch in hits:
            event[f'adc{ch:02d}'] = int(self.random_charge.read(ch))
            
        return event

    
    @classmethod
    def _node_creator_method(cls):
        def randomevent_device(self, n=4, rate=10, occupancy=0.5, t_mean=100, q_mean=100, q_sigma=10):
            return RandomEventDeviceNode(n=n, rate=rate, occupancy=occupancy, t_mean=t_mean, q_mean=q_mean, q_sigma=q_sigma)
        return randomevent_device
