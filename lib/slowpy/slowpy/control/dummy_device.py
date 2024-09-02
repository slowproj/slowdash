# Created by Sanshiro Enomoto on 5 June 2023 #

import time
import numpy as np


class RandomWalkDevice:
    def __init__(self, n=16, walk=1.0, decay=0.1, initial=0, tick=1.0):
        self.n = n
        self.walk = walk
        self.decay = decay
        self.tick = tick

        self.t = [time.time()] * n
        self.x0 = [initial] * n
        self.x = [initial] * n
        for ch in range(self.n):
            self.x[ch] = np.random.normal(self.x0[ch], 3*self.walk)


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
