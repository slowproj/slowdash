# Created by Sanshiro Enomoto on 17 July 2024 #

import numpy as np
from .basetypes import DataElement


class Graph(DataElement):
    def __init__(self, labels=['x', 'y']):
        super().__init__()
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
        if isinstance(x, (list, np.ndarray)):
            for v in [ y, z, x_err, y_err, z_err ]:
                if v is not None and (not isinstance(v, (list, np.ndarray)) or len(v) != len(x)):
                    # ERROR: ...
                    return
            for k in range(len(x)):
                self.add_point(
                    x[k], y[k],
                    z[k] if z is not None else None,
                    x_err[k] if x_err is not None else None,
                    y_err[k] if y_err is not None else None,
                    z_err[k] if z_err is not None else None
                )
            return
        else:
            for v in [ x, y, z, x_err, y_err, z_err ]:
                if v is not None and not isinstance(v, (int, float)):
                    # ERROR: ...
                    continue
            self.x.append(float(x) if x is not None else None)
            self.y.append(float(y) if y is not None else None)
            self.z.append(float(z) if z is not None else None)
            self.x_err.append(float(x_err) if x_err is not None else None)
            self.y_err.append(float(y_err) if y_err is not None else None)
            self.z_err.append(float(z_err) if z_err is not None else None)

            
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
    def from_json(obj):
        graph = Graph(obj.get('labels', ['x', 'y']))
        
        graph.y = obj.get('y', [])
        graph.x = obj.get('x', [xk for xk in range(len(graph.y))])
        graph.z = obj.get('z', [None]*len(graph.y))
        graph.x_err = obj.get('x_err', [None]*len(graph.y))
        graph.y_err = obj.get('y_err', [None]*len(graph.y))
        graph.z_err = obj.get('z_err', [None]*len(graph.y))
        
        return graph


    def to_numpy(self):
        obj = self.to_json()
        return (obj['x'], obj['y'], obj.get('y_err', None))

    
    
class GraphYStat:
    def __init__(self, fields=['n', 'y-mean', 'y-stdev'], ndigits=4):
        self.fields = fields
        self.ndigits = ndigits

        
    def __call__(self, graph):
        result = {}
        for key in self.fields:
            key2 = key[2:] if key[0:2].lower() == 'y-' else key
            if key.lower() in ['n', 'counts', 'entries']:
                result[key] = len(graph.y)
            elif key2.lower() in ['m', 'mean', 'average']:
                result[key] = round(np.mean(graph.y), self.ndigits)
            elif key2.lower() in ['sd', 'std', 'stdev', 'rms', 'sigma']:
                result[key] = round(np.std(graph.y), self.ndigits)
            else:
                result[key] = None
        return result
