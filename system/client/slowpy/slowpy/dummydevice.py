# Created by Sanshiro Enomoto on 5 June 2023 #


import time
import numpy as np


class DummyWalkDevice:
    def __init__(self, n=16, walk=1.0, decay=0.1, wait=1.0):
        self.n = n
        self.walk = walk
        self.decay = decay
        self.wait = wait
        
        self.x = [0] * n
        for ch in range(self.n):
            self.x[ch] = np.random.normal(0, 5*self.walk)

        
    def read(self):
        if self.wait > 0:
            time.sleep(self.wait)
            
        t = time.time()
        for ch in range(self.n):
            self.x[ch] = (1-self.decay) * self.x[ch] + np.random.normal(0, self.walk)
        return [ { "time": t, "channel": ch, "value": round(self.x[ch],3) } for ch in range(self.n) ]
