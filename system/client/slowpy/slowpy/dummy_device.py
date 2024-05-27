# Created by Sanshiro Enomoto on 5 June 2023 #


import time
import numpy as np
from .serial_device import ScpiDevice, SerialDeviceEthernetServer



class DummyDevice_RandomWalk:
    def __init__(self, n=16, center=0, walk=1.0, decay=0.1, tick=1.0):
        self.n = n
        self.center = center
        self.walk = walk
        self.decay = decay
        self.tick = tick

        self.t = [time.time()] * n
        self.x0 = [center] * n
        self.x = [center] * n
        for ch in range(self.n):
            self.x[ch] = np.random.normal(self.x0[ch], 10*self.walk)


    def channels(self):
        return range(self.n)
            
        
    def write(self, channel, value):
        if channel < 0 or channel >= len(self.x0):
            return
        
        self.x0[channel] = float(value)
        self.x[channel] = np.random.normal(self.x0[channel], self.walk)

        
    def read(self, channel):
        if channel >= len(self.x):
            return
        
        now = time.time()
        if self.tick > 0:
            steps = int((now - self.t[channel]) / self.tick)
            self.t[channel] = self.t[channel] + self.tick * steps
        else:
            steps = 1
            self.t[channel] = now
            
        for k in range(steps):
            self.x[channel] -= self.decay * (self.x[channel] - self.x0[channel]) + np.random.normal(0, self.walk)
        
        return round(self.x[channel], 3)



    
class DummyScpiDevice_RandomWalk(ScpiDevice):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.device = DummyDevice_RandomWalk(n=4, walk=1.0, decay=0.1, tick=0)
        self.errors = []

        
    def process_scpi_command(self, cmd_path, params):
        # SCPI commands:
        #   *IDN?, *OPC?, *RST, *CLS, SYSTem:ERRor?
        #   MEASure:V0?, MEASure:V1?, *MEASure:V2?, MEASure:V3?
        #   WALK?, WALK n.nn, DECAY?, DECAY n.nn
            
        if cmd_path[0] == '*IDN?':
            return 'Dummy SCPI Device'
        elif cmd_path[0] == '*OPC?':
            return '1'
        elif cmd_path[0] == '*RST':
            self.device.walk = 1.0
            self.device.decay = 0.1
            return ''
        elif cmd_path[0] == '*CLS':
            self.errors = []   # do not clear by *RST
            return ''
        elif cmd_path[0][0:4] == 'SYST' and cmd_path[1][0:3] == 'ERR':
            return self.errors.pop() if len(self.errors) > 0 else ''

        elif cmd_path[0][0:4] == 'MEAS' and cmd_path[1] == 'V0?':
            return '%f' % self.device.read(0)
        elif cmd_path[0][0:4] == 'MEAS' and cmd_path[1] == 'V1?':
            return '%f' % self.device.read(1)
        elif cmd_path[0][0:4] == 'MEAS' and cmd_path[1] == 'V2?':
            return '%f' % self.device.read(2)
        elif cmd_path[0][0:4] == 'MEAS' and cmd_path[1] == 'V3?':
            return '%f' % self.device.read(3)

        elif cmd_path[0][0:4] == 'MEAS' and cmd_path[1] == 'V0':
            try:
                self.device.x[0] = float(params[0])
            except:
                self.errors.append('-224,"Illegal parameter value: %s"' % ':'.join(cmd_path))
            return ''
        elif cmd_path[0][0:4] == 'MEAS' and cmd_path[1] == 'V1':
            try:
                self.device.x[1] = float(params[1])
            except:
                self.errors.append('-224,"Illegal parameter value: %s"' % ':'.join(cmd_path))
            return ''
        elif cmd_path[0][0:4] == 'MEAS' and cmd_path[1] == 'V2':
            try:
                self.device.x[2] = float(params[2])
            except:
                self.errors.append('-224,"Illegal parameter value: %s"' % ':'.join(cmd_path))
            return ''
        elif cmd_path[0][0:4] == 'MEAS' and cmd_path[1] == 'V3':
            try:
                self.device.x[3] = float(params[3])
            except:
                self.errors.append('-224,"Illegal parameter value: %s"' % ':'.join(cmd_path))
            return ''
        
        elif cmd_path[0] == 'WALK?':
            return '%f' % self.device.walk
        elif cmd_path[0] == 'DECAY?':
            return '%f' % self.device.decay

        elif cmd_path[0] == 'WALK' :
            try:
                self.device.walk = float(params[0])
            except:
                self.errors.append('-224,"Illegal parameter value: %s"' % ':'.join(cmd_path))
            return ''
        elif cmd_path[0] == 'DECAY':
            try:
                self.device.decay = float(params[0])
            except:
                self.errors.append('-224,"Illegal parameter value: %s"' % ':'.join(cmd_path))
            return ''
            
        else:
            self.errors.append('100,"Command error: %s"' % ':'.join(cmd_path))
            return ''
