# Created by Sanshiro Enomoto on 20 March 2022 #


import sys, os, math, logging
from datasource import DataSource, Schema

from redis import Redis
from redistimeseries.client import Client as RedisTimeSeries


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
        self.redis_json = None
        
        self.obj_channels = []
        
        try:
            import rejson
        except:
            logging.error('unable to load "rejson" python module')
            return
        try:
            self.redis_json = rejson.Client(host=host, port=port, db=db, decode_responses=True)
            logging.debug('RedisJSON loaded: %s:%s/%s' % (host, port, db))
        except Exception as e:
            logging.error(e)
            return

        
    def get_object(self, channels, length, to):
        record = {}
        start = to - length
        
        for ch in channels:
            if ch not in self.channels:
                continue
            key = ch[0:len(ch)-len(self.suffix)]
            try:
                obj = self.redis_json.jsonget(key)
            except Exception as e:
                logging.error('Redis: error on jsonget(): %s: %s' % (ch, str(e)))
                continue
            
            record[ch] = {
                'start': start, 'length': length,
                't': to,
                'x': obj if obj is not None else {}
            }

        return record

    
    def scan_channels(self):
        self.channels = {}
        
        if self.redis_json is None:
            return
        
        for key in self.redis.keys():
            if self.redis.type(key) != 'ReJSON-RL':
                continue
            objtype = self.find_object_type(key)
            if objtype is not None:
                self.channels[key+self.suffix] = { 'type': objtype }

    
    def find_object_type(self, name):
        if self.redis_json is None:
            return None
        
        try:
            obj = self.redis_json.jsonget(name)
        except Exception as e:
            logging.error('Redis: error on jsonget(): %s' % str(e))
            return None
        if obj is None:
            return None

        if 'table' in obj:
            return obj.get('type', 'table')
        elif 'tree' in obj:
            return obj.get('type', 'tree')
        elif 'bins' in obj:
            return obj.get('type', 'histogram')
        elif 'y' in obj:
            return obj.get('type', 'graph')
        else:
            return obj.get('type', 'json')

    
        
class TimeSeriesSource(ObjectSource):
    def __init__(self, host, port, db, config):
        super().__init__(host, port, db, config)
        if self.redis is None:
            return

        self.redis_ts = None
        try:
            self.redis_ts = RedisTimeSeries(host=host, port=port, db=db, decode_responses=True)
            logging.debug('RedisTS loaded: %s:%s/%s' % (host, port, db))
        except Exception as e:
            logging.error(e)

            
    def scan_channels(self):
        self.channels = {}
        if self.redis_ts is None:
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
                ts = self.redis_ts.range(key, int(1000*start), int(1000*to))
            except Exception as e:
                logging.warn('Redis: Unable load data: %s: %s' % (key, str(e)))
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
        if self.redis_ts is None or self.redis_json is None:
            return
        
        self.name_template = config.get('name_template', '{series}_{index:#d}')


    def get_timeseries(self, channels, length, to):
        return {}

    
    def get_object(self, channels, length, to):
        if self.redis_ts is None:
            return {}
        
        record = {}
        start = to - length

        for ch in channels:
            if ch not in self.channels:
                continue
            key = ch[0:len(ch)-len(self.suffix)]
            
            try:
                ts = self.redis_ts.range(key, int(1000*start), int(1000*to))
            except Exception as e:
                logging.warn('Redis: Unable load data: %s: %s' % (ch, str(e)))
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
            try:
                obj = self.redis_json.jsonget(name)
            except Exception as e:
                logging.warn('Redis: Unable load ObjTS JSON data: %s: %s' % (name, str(e)))
                continue

            record[ch] = {
                'start': start, 'length': length,
                't': math.floor(10*(tk/1000 - start))/10,
                'x': obj if obj is not None else {}
            }

        return record

    
    def scan_channels(self):
        self.channels = {}

        if self.redis_ts is None or self.redis_json is None:
            return

        for key in self.redis_json.keys():
            if self.redis_json.type(key) == 'TSDB-TYPE':
                objtype = self.find_object_type(key)
                if objtype is not None:
                    self.channels[key+self.suffix] = { 'type': objtype }
        

    def find_object_type(self, channel):
        try:
            tk, index = self.redis_ts.get(channel)
        except Exception as e:
            logging.error(e)
            return None

        name = self.name_template.format(series=channel, index=int(index))
        return super().find_object_type(name)
    
                    

class DataSource_Redis3(DataSource):
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
        
        for src in self.sources:
            src.scan_channels()

                    
    def get_channels(self):
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
