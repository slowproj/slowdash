# Created by Sanshiro Enomoto on 17 July 2024 #


import time, json
import numpy as np


class DataElement:
    def __init__(self):
        self.attr_values = {}
        self.stat_values = {}
        self.stat_functors = []

        
    def add_attr(self, name, value):
        self.attr_values[name] = value

        
    def add_stat(self, arg0, arg1=None):
        # add_stat(key, value) or add_stat(functor) where functor takes an DataElement and returns a dict
        if callable(arg0):
            self.stat_functors.append(arg0)
        else:
            self.stat_values[arg0] = arg1

        
    def clear(self):
        self.stat_values = {}

        
    def to_json(self):
        for f in self.stat_functors:
            self.stat_values.update(f(self))
        
        record = {}
        if any(self.attr_values):
            record.update({ '_attr': self.attr_values })
        if any(self.stat_values):
            record.update({ '_stat': self.stat_values })
        return record

    
    @staticmethod
    def from_json(name, obj):
        # this assumes that the user has already imported the histogram and graph modules
        if 'bins' in obj:
            return Histogram.from_json(name, obj)
        elif 'ybins' in obj:
            return Histogram2d.from_json(name, obj)
        elif 'y' in obj:
            return Graph.from_json(name, obj)
        return None

    
    def __str__(self):
        return json.dumps(self.to_json())



class TimeSeries:
    def __init__(self, fields=['x']):
        self.fields = fields if len(fields) > 0 else ['x']
        self.t = []
        self.values = []


    def write(values, time=None):
        '''
        # add one point to the time-series #
        - values: dict for field name-value pairs, or list for field values, or a value
                  where a value can be a number, string, or data-element.
        - time: UNIX time-stamp, if None if given, the current time will be used.
        '''
        if time is None:
            time = time.time()
        record = [None] * len(self.fields)
        
        if type(values) == dict:
            for i in len(record):
                record[i] = values.get(self.fields[i], None)
        elif type(values) == list:
            for i in range(min(len(values), len(record))):
                record[self.fields.keys()[i]] = values[i]
        else:
            record[0] = values

        self.t.append(time - self.start)
        self.values.append(record)


    def __str__(self):
        record = {
            't': self.t,
        }
        for k in range(len(self.fields)):
            record[self.fields[k]] = self.values[k]
        
        return json.dumps(record)
