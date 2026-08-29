# Created by Sanshiro Enomoto on 13 July 2026 #

import time, logging
from typing import Any

from .mesh import MeshPacket
from ..store import DataStore
from ..basetypes import TimeSeries


class DataPacket(MeshPacket):
    def __init__(self, values, tag=None, timestamp=None):
        '''
        Creates a SlowMesh packet for the "data.>" topics.
        The arguments are the same as slowpy.store.DataStore.append().
        - Arguments:
            - values: one of the followings:
                - scalar value, which is a number, string, or data-element,
                - dict for pairs of a field-name and a scalar-value, or
                - time-series, an instance of slowpy.TimeSeries.
            - tag: tag for channels. The channel names are composed of the tag values and field names.
            - time: UNIX time-stamp, if None is given, the current time will be used. Not used if values are time-series.
        '''

        self.values = values
        self.tag = tag
        self.timestamp = timestamp


    def pack(self, topic:str):
        '''
        - return value: tuple of (topic, headers, body)
        '''
            
        headers, body = {}, {}
        
        if isinstance(self.values, TimeSeries):
            if self.tag is None:
                logging.error(f'mesh.DataPacket: tag is required for time-series data type')
                return (topic, None, None)

            fields = self.values.fields
            values = self.values.values
            body = { self.tag: { fields[i]: values[i] for i in range(len(fields)) } }
        else:    
            t = self.timestamp if self.timestamp is not None else time.time()
            if type(t) in [ int, float ] and t <= 0:
                t += time.time()
                
            if type(self.values) is dict:
                prefix = f'{self.tag}:' if self.tag is not None else ''
                body = { prefix+field: { 't':t ,'x': x } for field, x in self.values.items() }
            elif self.tag is not None:
                body = { self.tag: { 't':t ,'x': self.values } }
            else:
                logging.error(f'mesh.DataPacket: unknown data type: {type(self.values)}')
                body = {}
                
        if self.tag is not None:
            topic = '.'.join([topic, self.tag])
            
        return (topic, headers, body)

            
    @classmethod
    def unpack(cls, headers, body):
        if not isinstance(body, dict):
            logging.error('mesh.DataPacket: received non-dict body')
            return MeshPacket()

        tag = None
        timestamp = None
        values = {}
        
        for ch, data in body.items():                
            t = data.get('t')
            if isinstance(t, list):
                if len(values) > 0:
                    logging.error('mesh.DataPacket: received badly formatted data: scalar and timeseries mixed')
                    continue  # skip only this data
                fields = [ str(key) for key in data.keys() if key != 't' ]
                values = TimeSereis(fields, start=data.get('start', 0), length=data.get('length', None))
                values.t = t
                values.values = [ data.get(field, None) for field in fields ]
                for v in values.values:
                    if len(v) != len(t):
                        logging.error('mesh.DataPacket: received badly formatted data: inconsistent field-data lengths')
                        
            elif isinstance(t, (int, float)):
                if isinstance(values, TimeSeries):
                    logging.error('mesh.DataPacket: received badly formatted data: scalar and timeseries mixed')
                    break
                if timestamp is None:
                    timestamp = t
                elif t is not None:
                    if abs(timestamp - t) > 1:
                        logging.error('mesh.DataPacket: received data with multiple distinct timestamps')
                values[ch] = data.get('x', None)
                
            else:
                logging.error(f'mesh.DataPacket: received data with a wrong time type: {type(t)}')

        if timestamp is None:
            logging.error('mesh.DataPacket: received data without a timestamp')
            timestamp = time.time()

        return DataPacket(values, tag=tag, timestamp=timestamp)
