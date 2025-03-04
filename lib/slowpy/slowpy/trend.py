# Created by Sanshiro Enomoto on 17 July 2024 #

import math, time, datetime
import numpy as np
from .basetypes import DataElement, TimeSeries
        

class Trend(DataElement):    
    def __init__(self, length=3600, tick=1, metric='mean', start=None):
        super().__init__()
        self.metric = metric
        self.tick = abs(tick)
        if start is None:
            self.start = int(time.time())
        else:
            self.start = start
        if length < self.tick:
            length = self.tick
        self.nbins = int(abs(length)/self.tick)
        
        self.count = np.zeros(self.nbins, dtype=np.float32)
        self.sum = np.zeros(self.nbins, dtype=np.float32)
        self.sum2 = np.zeros(self.nbins, dtype=np.float32)
        self.min = np.full(self.nbins, np.nan, dtype=np.float32)
        self.max = np.full(self.nbins, np.nan, dtype=np.float32)

        self.start_index = 0
        self.current_index = 0
        self.has_values = True
        
    
    def clear(self):
        super().clear()
        self.start_index = self.current_index
        k = int(self.current_index % self.nbins)
        self.count[k] = 0
        self.sum[k] = 0
        self.sum2[k] = 0
        self.min[k] = np.nan
        self.max[k] = np.nan


    def flush(self):
        # this does not remove the currently-being-filled bin
        self.start_index = self.current_index
        
        
    def evolve(self, time=None, complete=False):
        if time is None:
            time = time.time()
            
        this_index = int((time - self.start) / self.tick)
        if this_index < 0:
            return

        for index in range(self.current_index+1, this_index+1):
            k = int(index % self.nbins)
            self.count[k] = 0
            self.sum[k] = 0
            self.sum2[k] = 0
            self.min[k] = np.nan
            self.max[k] = np.nan
                
        if complete:
            self.current_index = this_index + 1
        else:
            self.current_index = this_index
            
        
    def fill(self, time=None, value=None, weight=1):
        if time is None:
            time = time.time()
            
        self.evolve(time)
        k = int(self.current_index % self.nbins)
        
        self.count[k] += weight
        if value is not None:
            self.sum[k] += weight*value
            self.sum2[k] += weight*value*value                
            self.min[k] = value if not (value > self.min[k]) else self.min[k]
            self.max[k] = value if not (value < self.max[k]) else self.max[k]
        else:
            self.has_values = False


    def timeseries(self, name, flush=False):
    # returns a time-series object
        ts = TimeSeries()
        ts.fields = []
        
        record = self.to_json()
        ts.t = [ t + self.start for t in record['x'] ]
        for key in record:
            if key == 'y':
                field = name
            elif key.startswith('y_'):
                field = f'{key[2:]}.{name}'
            else:
                continue
            ts.fields.append(field)
            ts.values.append(record[key])

        if flush:
            self.flush()
                
        return ts

    
    def to_json(self):
    # returns a graph object
        n = min(self.current_index - self.start_index, self.nbins-1)
        indexes = [ int((self.current_index - n + k) % self.nbins) for k in range(n) ]
        lapse = [ self.tick/2 + self.tick * (self.current_index - n + k) for k in range(n) ]
        
        self.attr_values['start_timestamp'] = self.start
        record = { **super().to_json(),  **{
            'labels': [ 'lapse', self.metric ],
            'x': lapse,
            'y': []
        }}
        
        if self.metric.lower() in [ 'count', 'counts', 'n', 'entries', 'events' ]:
            record['y'] = self.count[indexes].tolist()
            record['y_err'] = np.sqrt(self.count[indexes]).tolist()
            return record
        elif self.metric.lower() in [ 'rate', 'rates', 'cps' ]:
            record['y'] = (self.count[indexes]/self.tick).tolist()
            record['y_err'] = (np.sqrt(self.count[indexes])/self.tick).tolist()
            return record

        if not self.has_values:
            record['y'] = np.full(n, np.nan).tolist()
            return record
            
        if self.metric.lower() in [ 'sum' ]:
            record['y'] = self.sum[indexes].tolist()
            return record

        with np.errstate(divide='ignore'):
            mean = self.sum[indexes] / self.count[indexes]
            variance = np.maximum(self.sum2[indexes]/self.count[indexes] - mean*mean, np.zeros(n))
                    
        if self.metric.lower() in [ 'mean', 'average' ]:
            record['y'] = mean.tolist()
            record['y_err'] = np.sqrt((variance)/self.count[indexes]).tolist()
            record['y_min'] = self.min[indexes].tolist()
            record['y_max'] = self.max[indexes].tolist()
            return record
        elif self.metric.lower() in [ 'rms', 'sd', 'std', 'stdev' ]:
            record['y'] = np.sqrt(variance).tolist()
            return record
        
        record['y'] = np.full(n, np.nan).tolist()
        return record

    
    @staticmethod
    def from_json(obj):
        return None

    
    def to_numpy(self):
        obj = self.to_json()
        t = [datetime.datetime.fromtimestamp(self.start+t) for t in obj['x']]
        x = obj['y']
        x_err = obj.get('y_err', None)
        return (t, x, x_err)

    

class RateTrend(Trend):
    def __init__(self, length=3600, tick=1, start=None):
        super().__init__(length=length, tick=tick, start=start, metric='cps')
