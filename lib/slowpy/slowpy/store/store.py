# Created by Sanshiro Enomoto on 3 June 2023 #

import time, atexit
from ..basetypes import TimeSeries


class DataStore:
    def __init__(self):
        # call self.close() before dependent DB modules are cleaned up (__del__() might be too late)
        try:
            atexit.register(self._atexit_close)
        except:
            pass


    def __del__(self):
        try:
            self.close()
        except:
            pass
        
        
    def _atexit_close(self):
        try:
            self.close()
        except:
            pass
        
        
    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
    
    
    def close(self):
        # this might be called multiple times
        pass
    

    def append(self, values, tag=None, timestamp=None):
        '''
        - values: one of the followings:
            - scalar value, which is a number, string, or data-element,
            - dict for pairs of a field-name and a scalar-value, or
            - time-series, an instance of slowpy.TimeSeries.
        - tag: tag for channels. The channel names are composed of the tag values and field names.
        - time: UNIX time-stamp, if None is given, the current time will be used. Not used if values are time-series.
        '''
        
        self._write(values, tag, timestamp, update=False)

        
    def update(self, values, tag=None, timestamp=None):
        '''
        Same as append(), but the existing data of the same channel will be deleted before writing
        '''
        
        self._write(values, tag, timestamp, update=True)

        
    def _write(self, values, tag=None, timestamp=None, update=False):                
        if isinstance(values, TimeSeries):
            ts = values
            records = []
            for i in range(len(ts.t)):
                fields, values = [], []
                for k in range(len(ts.fields)):
                    if ts.values[k][i] is not None:
                        fields.append(ts.fields[k])
                        values.append(ts.values[k][i])
                if len(fields) > 0:
                    records.append((ts.start+ts.t[i], fields, values))
                
            if len(records) > 0:
                handle = self._open_transaction()
                if handle is not None:
                    for row in records:
                        self._write_one(handle, timestamp=row[0], tag=tag, fields=row[1], values=row[2], update=update)
                    self._close_transaction(handle)
                
        else:
            t = timestamp if timestamp is not None else time.time()
            if type(t) in [ int, float ] and t <= 0:
                t += time.time()
            
            if type(values) is dict:
                fields = [ k for k in values.keys() ]
                values = [ v for v in values.values() ]
            else:
                fields = None
                values = [ values ]
                
            handle = self._open_transaction()
            if handle is not None:
                self._write_one(handle, timestamp=t, tag=tag, fields=fields, values=values, update=update)
                self._close_transaction(handle)
                

    # override in child classes
    def _open_transaction(self):
        # return a handle on success, else return None
        return None

    
    # override in child classes
    def _close_transaction(self, handle):
        pass

    
    # override in child classes
    def _write_one(self, handle, timestamp, tag, fields, values, update):
        '''
        - fields: list of names, or None
        - values: list of values, where a value can be a number, string or data-element.
        - update: if True the exising data of the same channel will be deleted before writing
        '''
        pass

    
    # use this in child classes
    @staticmethod
    def _channels(tag, fields):
        channels = []

        for field in (fields or ([''] if tag is not None else [])):
            if tag is not None and len(field) > 0:
                ch = '%s:%s' % (tag, field)
            elif tag is not None:
                ch = tag
            elif len(field) > 0:
                ch = field
            else:
                ch = '__unnamed'
            channels.append(ch)

        return channels

        

    
class DataStore_Null(DataStore):
    pass
