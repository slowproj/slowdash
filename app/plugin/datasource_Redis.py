# Created by Sanshiro Enomoto on 20 March 2022 #


import sys, os, time, math, logging
from sd_dataschema import Schema
from sd_datasource import DataSource

from redis import Redis

objts_prefix = '__sd_objts'


class KeyValueSource:
    def __init__(self, host, port, db, params):
        self.suffix = params.get('suffix', '')
        
        self.channels = {}
        self.redis = None
        
        for i in range(12):
            try:
                self.redis = Redis(host=host, port=port, db=db, decode_responses=True)
                self.redis.keys()
                break
            except Exception as e:
                logging.info(f'Unable to connect to Redis: {e}')
                logging.info(f'retrying in 5 sec... ({i+1}/12)')
                time.sleep(5)
        else:
            logging.error(f'Unable to connect to Redis: "{host}:{port}/{db}"')
            logging.error(traceback.format_exc())
            self.redis = None

        if self.redis is not None:
            logging.debug('Redis loaded: %s:%s/%s' % (host, port, db))

        
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
        if self.redis is None:
            return
        
        for key in self.redis.keys():
            if key.startswith(objts_prefix):
                continue
            if self.redis.type(key) == 'hash':
                self.channels[key+self.suffix] = { 'type': 'tree' }

                
        
class ObjectSource(KeyValueSource):
    def __init__(self, host, port, db, params):
        super().__init__(host, port, db, params)
        
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
            if key.startswith(objts_prefix):
                continue
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
    def __init__(self, host, port, db, params):
        super().__init__(host, port, db, params)
        if self.redis is None:
            return

            
    def scan_channels(self):
        self.channels = {}
        if self.redis is None:
            return
        
        for key in self.redis.keys():
            if key.startswith(objts_prefix):
                continue
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
                logging.warning('Redis: Unable load TS data: %s: %s' % (key, str(e)))
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
    def __init__(self, host, port, db, params):
        super().__init__(host, port, db, params)

        
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
            
            tsname = '%sindex_%s' % (objts_prefix, key)
            try:
                ts = self.redis.ts().range(tsname, int(1000*start), int(1000*to))
            except Exception as e:
                logging.warning('Redis: Unable load TS data: %s: %s' % (ch, str(e)))
                continue
            if len(ts) < 1:
                record[ch] = {
                    'start': start, 'length': length,
                    't': to,
                    'x': {}
                }
                continue

            tk, index = ts[len(ts)-1]
            objname = '%s_%s_%d' % (objts_prefix, key, int(index))
            if key in self.json_str_channels:
                try:
                    obj = self.redis.get(objname)
                except Exception as e:
                    logging.error('Redis: error on get(): %s: %s' % (ch, str(e)))
                    continue
            else:
                try:
                    obj = self.redis.json().get(objname)
                except Exception as e:
                    logging.warning('Redis: error on json().get(): %s: %s' % (objname, str(e)))
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
            if not key.startswith(objts_prefix):
                continue
            if self.redis.type(key) != 'TSDB-TYPE':
                continue
            name = key[len(objts_prefix+'index_'):]
            objtype, keytype = self.find_object_type(name)
            if objtype is not None:
                self.channels[name+self.suffix] = { 'type': objtype }
                if keytype == 'string':
                    self.json_str_channels.add(name)
        

    def find_object_type(self, name):
        tskey = objts_prefix + 'index_' + name
        try:
            tk, index = self.redis.ts().get(tskey)
        except Exception as e:
            return None, None

        return super().find_object_type('%s_%s_%d' % (objts_prefix, name, int(index)))
    
                    

class DataSource_Redis(DataSource):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)

        dburl = Schema.parse_dburl(params.get('url', ''))
        host = dburl.get('host', 'localhost')
        port = dburl.get('port', '6379')
        default_db = dburl.get('db', None)

        def load_source(params, entrytype, source_class):
            source_list = []
            entry_list = params.get(entrytype, [])
            for entry in entry_list if type(entry_list) is list else [ entry_list ]:
                db = entry.get('db', default_db)
                source_list.append(source_class(host, port, db, entry))
            return source_list
        
        self.kv_sources = load_source(params, 'key_value', KeyValueSource)
        self.obj_sources = load_source(params, 'object', ObjectSource)
        self.ts_sources = load_source(params, 'time_series', TimeSeriesSource)
        self.objts_sources =  load_source(params, 'object_time_series', ObjectTimeSeriesSource)
        self.sources = self.kv_sources + self.obj_sources + self.ts_sources + self.objts_sources
        
        if default_db is not None and len(self.sources) == 0:
            self.kv_sources = [ KeyValueSource(host, port, default_db, {}) ]
            self.obj_sources = [ ObjectSource(host, port, default_db, {}) ]
            self.ts_sources = [ TimeSeriesSource(host, port, default_db, {}) ]
            self.objts_sources = [ ObjectTimeSeriesSource(host, port, default_db, {}) ]
            self.sources = self.kv_sources + self.obj_sources + self.ts_sources + self.objts_sources
            
        for src in self.sources:
            src.scan_channels()
        
                    
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
