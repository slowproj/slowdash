# Created by Sanshiro Enomoto on 3 June 2023 #


import numpy as np
import datetime
import json


class DataObject:
    def __init__(self):
        self.attr_values = {}
        self.stat_values = {}
        self.stat_functors = []

        
    def add_attr(self, name, value):
        self.attr_values[name] = value

        
    def add_stat(self, arg0, arg1=None):
        # add_stat(key, value) or add_stat(functor) where functor takes an DataObject and returns a dict
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
        if 'bins' in obj:
            return Histogram.from_json(name, obj)
        elif 'ybins' in obj:
            return Histogram2d.from_json(name, obj)
        elif 'y' in obj:
            return Graph.from_json(name, obj)
        return None
    
    def __str__(self):
        return json.dumps(self.to_json())



class HistogramScale:
    def __init__(self, nbins, range_min, range_max):
        self.nbins = max(nbins, 0)
        self.min = min(range_min, range_max)
        self.max = max(range_min, range_max)
        if not (self.min < self.max):
            self.nbins = 0
        elif self.nbins > 0:
            self.bin_width = (self.max - self.min) / self.nbins

            
    def get_bin_of(self, value):
        if self.nbins <= 0 or value < self.min or value >= self.max:
            return None
        return int((value - self.min) / self.bin_width)

    
    def get_bin_range_of(self, bin_index):
        if self.nbins <= 0:
            return (None, None)
        left = self.min + bin_index * self.bin_width
        right = left + self.bin_width
        return (left, right)


    
class Histogram(DataObject):
    def __init__(self, name, nbins, range_min, range_max):
        super().__init__()
        self.name = name
        self.scale = HistogramScale(nbins, range_min, range_max)
        if self.scale.nbins > 0:
            self.counts = [0] * self.scale.nbins
        else:
            self.counts = []
        self.overflow, self.underflow = 0, 0

        
    def clear(self):
        super().clear()
        self.counts[:] = 0
        self.overflow, self.underflow = 0, 0

        
    def fill(self, value, weight=1):
        bin = self.scale.get_bin_of(value)
        if bin is not None:
            self.counts[bin] += weight
        else:
            if value < self.scale.min:
                self.underflow += weight
            if value >= self.scale.max:
                self.overflow += weight

                
    def rebin(self, nbins, range_min, range_max):
        if nbins <= 0:
            return
        new_scale = HistogramScale(nbins, range_min, range_max)
        new_counts = [0] * new_scale.nbins
        for bin in range(self.scale.nbins):
            (left, right) = self.scale.get_bin_range_of(bin)
            for k in range(int(self.counts[bin])):
                value = np.random.uniform(left, right)
                new_bin = new_scale.get_bin_of(value)
                if new_bin is not None:
                    new_counts[new_bin] += 1
        self.scale = new_scale
        self.counts = new_counts

        
    def to_json(self):
        return { **super().to_json(),  **{
            'bins': { 'min': self.scale.min, 'max': self.scale.max },
            'counts': self.counts
        }}

    
    @staticmethod
    def from_json(name, obj):
        bins, counts = obj['bins'], obj['counts']
        hist = Histogram(name, len(counts), bins['min'], bins['max'])
        hist.counts = counts
        return hist
        

    
class Histogram2d(DataObject):
    def __init__(self, name, xnbins, xrange_min, xrange_max, ynbins, yrange_min, yrange_max):
        super().__init__()
        self.name = name
        self.xscale = HistogramScale(xnbins, xrange_min, xrange_max)
        self.yscale = HistogramScale(ynbins, yrange_min, yrange_max)
        if self.xscale.nbins > 0 and self.yscale.nbins > 0:
            self.counts = [ [0]*self.xscale.nbins for yslice in range(self.yscale.nbins) ]
        else:
            self.counts = None
        self.outliers = 0

        
    def clear(self):
        super().clear()
        for yslice in self.counts:
            yslice[:] = 0
        self.outliers = 0

        
    def fill(self, x, y, weight=1):
        xbin = self.xscale.get_bin_of(x)
        ybin = self.yscale.get_bin_of(y)
        if self.counts is None or xbin is None or ybin is None:
            self.outliers += weight
        else:
            self.counts[ybin][xbin] += weight

                
    def to_json(self):
        return { **super().to_json(),  **{
            'xbins': { 'min': self.xscale.min, 'max': self.xscale.max },
            'ybins': { 'min': self.yscale.min, 'max': self.yscale.max },
            'counts': self.counts
        }}

    
    @staticmethod
    def from_json(name, obj):
        xbins, ybins, counts = obj['xbins'], obj['ybins'], obj['counts']
        hist = Histogram2d(name, len(counts[0]), xbins['min'], xbins['max'], len(counts), ybins['min'], ybins['max'])
        hist.counts = counts
        return hist
        

    
class Graph(DataObject):
    def __init__(self, name, labels=['x', 'y']):
        super().__init__()
        self.name = name
        self.labels = labels
        self.clear()

        
    def clear(self):
        super().clear()
        self.x = []
        self.y = []
        self.z = []
        self.x_err = []
        self.y_err = []
        self.z_err = []


    def has_z(self):
        return any(val is not None for val in self.z)

    def has_x_err(self):
        return any(val is not None for val in self.x_err)

    def has_y_err(self):
        return any(val is not None for val in self.y_err)

    def has_z_err(self):
        return any(val is not None for val in self.z_err)

            
    def add_point(self, x, y, z=None, x_err=None, y_err=None, z_err=None):
        if type(x) is list:
            for v in [ y, z, x_err, y_err, z_err ]:
                if v is not None and (type(v) is not list or len(v) != len(x)):
                    # ERROR: ...
                    return
            for k in range(len(x)):
                self.add_point(x[k], y[k], z[k], x_err[k], y_err[k], z_err[k])
                return
        else:
            for v in [ x, y, z, x_err, y_err, z_err ]:
                if v is not None and not isinstance(v, (int, float)):
                    # ERROR: ...
                    continue
            self.x.append(x)
            self.y.append(y)
            self.z.append(z)
            self.x_err.append(x_err)
            self.y_err.append(y_err)
            self.z_err.append(z_err)

            
    def to_json(self):
        record = { **super().to_json(),  **{
            'labels': self.labels,
            'x': self.x,
            'y': self.y
        }}
        if self.has_z():
            record['z'] = self.z
        if self.has_x_err():
            record['x_err'] = self.x_err
        if self.has_y_err():
            record['y_err'] = self.y_err
        if self.has_z_err():
            record['z_err'] = self.z_err
            
        return record

    
    @staticmethod
    def from_json(name, obj):
        graph = Graph(name, obj.get('labels', ['x', 'y']))
        
        graph.y = obj.get('y', [])
        graph.x = obj.get('x', [xk for xk in range(len(graph.y))])
        graph.z = obj.get('z', [None]*len(graph.y))
        graph.x_err = obj.get('x_err', [None]*len(graph.y))
        graph.y_err = obj.get('y_err', [None]*len(graph.y))
        graph.z_err = obj.get('z_err', [None]*len(graph.y))
        
        return graph


    
class Table(DataObject):
    def __init__(self, name, columns):
        super().__init__()
        self.name = name
        self.columns = columns
        self.tabular = []

    def clear(self):
        super().clear()
        self.tabular = []
        
    def add_row(self, array_of_values):
        self.tabular.append(array_of_values)
    
    def to_json(self):
        return { **super().to_json(),  **{
            'columns': self.columns,
            'table': self.tabular
        }}


    
class Log(Table):
    def __init__(self, name="Log", dateformat='%a, %b %d %Y, %H:%M:%S'):
        super().__init__(name, columns=['Level', 'Time', 'Message'])
        self.dateformat = dateformat

    def write(self, level, message):
        self.tabular.append([ level, datetime.datetime.now().strftime(self.dateformat), message ])
    
    def debug(self, message):
        self.write('Debug', message)

    def info(self, message):
        self.write('Info', message)

    def warn(self, message):
        self.write('Warn', message)

    def error(self, message):
        self.write('Error', message)


    
class Record(DataObject):
    def __init__(self, name, path_delimiter='/'):
        super().__init__()
        self.name = name
        self.path_delimiter = path_delimiter
        self.record = {}

    def clear(self):
        super().clear()
        self.record = {}
        
    def set(self, key, value):
        def add(node, path, value):
            if len(path) < 1:
                pass
            if len(path) == 1:
                node[path[0]] = value
            elif len(path) > 1:
                if path[0] not in node:
                    node[path[0]] = {}
                add(node[path[0]], path[1:], value)
        add(self.record, key.split(self.path_delimiter), value)
    
    def to_json(self):
        return { **super().to_json(),  **{
            'tree': self.record
        }}


    
class RateTrendGraph(DataObject):
    def __init__(self, name, length=3600, tick=1, start=0):
        super().__init__()
        self.name = name
        self.start = start
        self.tick = tick
        self.nbins = int(length/tick)

        if self.nbins > 0:
            self.counts = [0] * self.nbins
        else:
            self.counts = []
        self.last_bin = -1
        self.last_bin_time = start

    def clear(self):
        super().clear()
        self.counts[:] = 0
        self.last_bin = -1
        self.last_bin_time = self.start
        
    def fill(self, time, weight=1):
        bin_index = int((time - self.start) / self.tick)
        for k in range(self.last_bin+1, bin_index):
            self.counts[int(k % self.nbins)] = 0
        if bin_index > self.last_bin:
            self.counts[int(bin_index % self.nbins)] = weight
        else:
            self.counts[int(bin_index % self.nbins)] += weight
        self.last_bin = bin_index
        
    def to_json(self):
        x, y = [], []
        for k in range(self.nbins-1):
            bin_index = self.last_bin - self.nbins + 1 + k
            if bin_index >= 0:
                x.append(self.start + (bin_index + 0.5) * self.tick)
                y.append(self.counts[bin_index % self.nbins] / float(self.tick))
        return { **super().to_json(),  **{
            'labels': ['time', 'cps'],
            'x': x, 'y': y
        }}
