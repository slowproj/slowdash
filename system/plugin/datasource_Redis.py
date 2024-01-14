# Created by Sanshiro Enomoto on 20 March 2022 #


import sys, os, math, logging
from datasource import DataSource, Schema

from redis import Redis


class KeyValueSource:
    def __init__(self, host, port, db, config):
        self.suffix = config.get('suffix', '')
        
        self.channels = {}
        self.redis = None
        
        try:
            self.redis = Redis(host=host, port=port, db=db, decode_responses=True)
            logging.debug('Redis loaded: %s:%s/%s' % (host, port, db))
        except Exception as e:
            logging.error(e)
            return

        
    def get_channels(self):
        return [ { **{'name': key}, **val } for key, val in self.channels.items() ]

    
    def get_timeseries(self, channels, length, to):
        return {}

    
    def get_object(self, channels, length, to):
        record = {}
        start = to - length
        
        for ch in channels:
            if ch not in self.channels:
                continue
            key = ch[0:len(ch)-len(self.suffix)]
            try:
                value = self.redis.hgetall(key)
            except Exception as e:
                logging.error('Redis: error on hgetall(): %s: %s' % (ch, str(e)))
                continue
            record[ch] = {
                'start': start, 'length': length,
                't': to,
                'x': { 'tree': value }
            }
                
        return record

    
    def scan_channels(self):
        self.channels = {}
        
        for key in self.redis.keys():
            if self.redis.type(key) == 'hash':
                self.channels[key+self.suffix] = { 'type': 'tree' }

                
        
class ObjectSource(KeyValueSource):
    def __init__(self, host, port, db, config):
        super().__init__(host, port, db, config)
        
        self.channels = {}
        self.json_str_channels = set()
        
        
    def get_object(self, channels, length, to):
        record = {}
        start = to - length
        
        for ch in channels:
            if ch not in self.channels:
                continue
            key = ch[0:len(ch)-len(self.suffix)]
            if key in self.json_str_channels:
                try:
                    obj = self.redis.get(key)
                except Exception as e:
                    logging.error('Redis: error on get(): %s: %s' % (ch, str(e)))
                    continue
            else:
                try:
                    obj = self.redis.json().get(key)
                except Exception as e:
                    logging.error('Redis: error on json().get(): %s: %s' % (ch, str(e)))
                    continue
            
            record[ch] = {
                'start': start, 'length': length,
                't': to,
                'x': obj if obj is not None else {}
            }

        return record

    
    def scan_channels(self):
        self.channels = {}
        
        if self.redis is None:
            return
        
        for key in self.redis.keys():
            objtype, keytype = self.find_object_type(key)
            if objtype is not None:
                self.channels[key+self.suffix] = { 'type': objtype }
                if keytype == 'string':
                    self.json_str_channels.add(key)
                    
    
    def find_object_type(self, key):
        if self.redis is None:
            return None
        
        keytype = self.redis.type(key)
        if keytype == 'string':
            try:
                obj = self.redis.get(key)
            except Exception as e:
                logging.error('Redis: error on json().get(): %s' % str(e))
                obj = None
        elif keytype == 'ReJSON-RL':
            try:
                obj = self.redis.json().get(key)
            except Exception as e:
                logging.error('Redis: error on json().get(): %s' % str(e))
                obj = None
        else:
            obj = None

        return Schema.identify_datatype(obj), keytype

    
        
class TimeSeriesSource(ObjectSource):
    def __init__(self, host, port, db, config):
        super().__init__(host, port, db, config)
        if self.redis is None:
            return

            
    def scan_channels(self):
        self.channels = {}
        if self.redis is None:
            return
        
        for key in self.redis.keys():
            if self.redis.type(key) == 'TSDB-TYPE':
                self.channels[key+self.suffix] = { 'type': 'timeseries' }


    def get_timeseries(self, channels, length, to):
        record = {}
        start = to - length
        
        for ch in channels:
            if ch not in self.channels:
                continue
            key = ch[0:len(ch)-len(self.suffix)]
            try:
                ts = self.redis.ts().range(key, int(1000*start), int(1000*to))
            except Exception as e:
                logging.warn('Redis: Unable load TS data: %s: %s' % (key, str(e)))
                continue
                
            t, x = [],[]
            for tk, xk in ts:
                t.append(int(10*(tk/1000-start))/10)
                x.append(xk)
            record[ch] = { 'start': start, 'length': length, 't': t, 'x': x }

        return record

    
    def get_object(self, channels, length, to):
        return {}

    
                             
class ObjectTimeSeriesSource(TimeSeriesSource):
    def __init__(self, host, port, db, config):
        super().__init__(host, port, db, config)
        
        self.name_template = config.get('name_template', '{series}_{index:#d}')


    def get_timeseries(self, channels, length, to):
        return {}

    
    def get_object(self, channels, length, to):
        if self.redis is None:
            return {}
        
        record = {}
        start = to - length

        for ch in channels:
            if ch not in self.channels:
                continue
            key = ch[0:len(ch)-len(self.suffix)]
            
            try:
                ts = self.redis.ts().range(key, int(1000*start), int(1000*to))
            except Exception as e:
                logging.warn('Redis: Unable load TS data: %s: %s' % (ch, str(e)))
                continue
            if len(ts) < 1:
                record[ch] = {
                    'start': start, 'length': length,
                    't': to,
                    'x': {}
                }
                continue

            tk, index = ts[len(ts)-1]
            name = self.name_template.format(series=key, index=int(index))
            if key in self.json_str_channels:
                try:
                    obj = self.redis.get(name)
                except Exception as e:
                    logging.error('Redis: error on get(): %s: %s' % (ch, str(e)))
                    continue
            else:
                try:
                    obj = self.redis.json().get(name)
                except Exception as e:
                    logging.warn('Redis: error on json().get(): %s: %s' % (name, str(e)))
                    continue

            record[ch] = {
                'start': start, 'length': length,
                't': math.floor(10*(tk/1000 - start))/10,
                'x': obj if obj is not None else {}
            }

        return record

    
    def scan_channels(self):
        self.channels = {}

        if self.redis is None:
            return

        for key in self.redis.keys():
            if self.redis.type(key) == 'TSDB-TYPE':
                objtype, keytype = self.find_object_type(key)
                if objtype is not None:
                    self.channels[key+self.suffix] = { 'type': objtype }
                    if keytype == 'string':
                        self.json_str_channels.add(key)
        

    def find_object_type(self, channel):
        try:
            tk, index = self.redis.ts().get(channel)
        except Exception as e:
            logging.error(e)
            return None, None

        name = self.name_template.format(series=channel, index=int(index))
        return super().find_object_type(name)
    
                    

class DataSource_Redis(DataSource):
    def __init__(self, project_config, config):
        super().__init__(project_config, config)

        dburl = Schema.parse_dburl(self.config.get('url', ''))
        host = dburl.get('host', 'localhost')
        port = dburl.get('port', '6379')
        default_db = dburl.get('db', None)

        def load_source(config, entrytype, source_class):
            source_list = []
            entry_list = config.get(entrytype, [])
            for entry in entry_list if type(entry_list) is list else [ entry_list ]:
                db = entry.get('db', default_db)
                source_list.append(source_class(host, port, db, entry))
            return source_list
        
        self.kv_sources = load_source(config, 'key_value', KeyValueSource)
        self.obj_sources = load_source(config, 'object', ObjectSource)
        self.ts_sources = load_source(config, 'time_series', TimeSeriesSource)
        self.objts_sources =  load_source(config, 'object_time_series', ObjectTimeSeriesSource)
        self.sources = self.kv_sources + self.obj_sources + self.ts_sources + self.objts_sources
        
        if default_db is not None and len(self.sources) == 0:
            self.kv_sources = [ KeyValueSource(host, port, default_db, {}) ]
            self.obj_sources = [ ObjectSource(host, port, default_db, {}) ]
            self.ts_sources = [ TimeSeriesSource(host, port, default_db, {}) ]
            self.sources = self.kv_sources + self.obj_sources + self.ts_sources
        
                    
    def get_channels(self):
        for src in self.sources:
            src.scan_channels()

        channels = []
        for src in self.sources:
            channels.extend([ k for k in src.get_channels() ])
        return channels

    
    def get_timeseries(self, channels, length, to, resampling=None, reducer='last'):
        record = {}
        for src in self.sources:
            record.update(src.get_timeseries(channels, length, to))

        if resampling is None:
            return record
            
        return self.resample(record, length, to, resampling, reducer)

                             
    def get_object(self, channels, length, to):
        record = {}
        for src in self.sources:
            record.update(src.get_object(channels, length, to))

        return record
