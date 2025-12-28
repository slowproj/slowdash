# Created by Sanshiro Enomoto on 20 March 2022 #


import sys, os, asyncio, time, math, logging, traceback
from sd_dataschema import Schema
from sd_datasource import DataSource

import redis.asyncio as aioredis


objts_prefix = '__sd_objts'


class KeyValueSource:
    def __init__(self, url, params):
        self.url = url
        self.suffix = params.get('suffix', '')
        
        self.redis = None
        self.channels = None

        
    async def connect(self):
        if self.redis is not None:
            return
        
        for i in range(12):
            try:
                self.redis = aioredis.from_url(self.url, decode_responses=True)
                await asyncio.wait_for(self.redis.keys(), timeout=0.1)
                break
            except Exception as e:
                if self.redis is not None:
                    try:
                        await self.redis.close()
                    except:
                        pass
                    self.redis = None
                logging.info(f'Unable to connect to Redis: {e}')
                logging.info(f'retrying in 5 sec... ({i+1}/12)')
                time.sleep(5)
        else:
            if self.redis is not None:
                try:
                    await self.redis.close()
                except:
                    pass
                self.redis = None
            logging.error(f'Unable to connect to Redis: {self.url}')
            logging.error(traceback.format_exc())

        if self.redis is not None:
            logging.info(f'Redis loaded for {self.__class__.__name__}: {self.url}')

        
    async def close(self):
        if self.redis is not None:
            await self.redis.close()
        self.redis = None

        
    async def get_channels(self):
        if self.channels is None:
            await self.scan_channels()
        return [ { **{'name': key}, **val } for key, val in self.channels.items() ]

    
    async def get_timeseries(self, channels, length, to):
        return {}

    
    async def get_object(self, channels, length, to):
        if self.channels is None:
            await self.scan_channels()
            
        record = {}
        start = to - length
        
        for ch in channels:
            if ch not in self.channels:
                continue
            key = ch[0:len(ch)-len(self.suffix)]
            try:
                value = await self.redis.hgetall(key)
            except Exception as e:
                logging.error('Redis: error on hgetall(): %s: %s' % (ch, str(e)))
                continue
            record[ch] = {
                'start': start, 'length': length,
                't': to,
                'x': { 'tree': value }
            }
                
        return record

    
    async def scan_channels(self):
        self.channels = {}
        if self.redis is None:
            return
        
        for key in await self.redis.keys():
            if key.startswith(objts_prefix):
                continue
            if await self.redis.type(key) == 'hash':
                self.channels[key+self.suffix] = { 'type': 'tree' }

                
        
class ObjectSource(KeyValueSource):
    def __init__(self, url, params):
        super().__init__(url, params)
        
        self.json_str_channels = set()
        
        
    async def get_object(self, channels, length, to):
        if self.channels is None:
            await self.scan_channels()
            
        record = {}
        start = to - length
        
        for ch in channels:
            if ch not in self.channels:
                continue
            key = ch[0:len(ch)-len(self.suffix)]
            if key in self.json_str_channels:
                try:
                    obj = DataSource.decode_if_json(await self.redis.get(key))
                except Exception as e:
                    logging.error('Redis: error on get(): %s: %s' % (ch, str(e)))
                    continue
            else:
                try:
                    obj = await self.redis.json().get(key)
                except Exception as e:
                    logging.error('Redis: error on json().get(): %s: %s' % (ch, str(e)))
                    continue
            
            record[ch] = {
                'start': start, 'length': length,
                't': to,
                'x': obj if obj is not None else {}
            }

        return record

    
    async def scan_channels(self):
        self.channels = {}
        if self.redis is None:
            return
        
        for key in await self.redis.keys():
            if key.startswith(objts_prefix):
                continue
            objtype, keytype = await self.find_object_type(key)
            if objtype is not None:
                self.channels[key+self.suffix] = { 'type': objtype }
                if keytype == 'string':
                    self.json_str_channels.add(key)
                    
    
    async def find_object_type(self, key):
        if self.redis is None:
            return None
        
        keytype = await self.redis.type(key)
        if keytype == 'string':
            try:
                obj = DataSource.decode_if_json(await self.redis.get(key))
            except Exception as e:
                logging.error('Redis: error on json().get(): %s' % str(e))
                obj = None
        elif keytype == 'ReJSON-RL':
            try:
                obj = await self.redis.json().get(key)
            except Exception as e:
                logging.error('Redis: error on json().get(): %s' % str(e))
                obj = None
        else:
            obj = None

        return Schema.identify_datatype(obj), keytype

    
        
class TimeSeriesSource(ObjectSource):
    def __init__(self, url, params):
        super().__init__(url, params)

            
    async def scan_channels(self):
        self.channels = {}
        if self.redis is None:
            return
        
        for key in await self.redis.keys():
            if key.startswith(objts_prefix):
                continue
            if await self.redis.type(key) == 'TSDB-TYPE':
                self.channels[key+self.suffix] = { 'type': 'numeric' }


    async def get_timeseries(self, channels, length, to):
        if self.channels is None:
            await self.scan_channels()
            
        record = {}
        start = to - length
        
        for ch in channels:
            if ch not in self.channels:
                continue
            key = ch[0:len(ch)-len(self.suffix)]
            try:
                ts = await self.redis.ts().range(key, int(1000*start), int(1000*to))
            except Exception as e:
                logging.warning('Redis: Unable load TS data: %s: %s' % (key, str(e)))
                continue
                
            t, x = [],[]
            for tk, xk in ts:
                t.append(int(10*(tk/1000-start))/10)
                x.append(xk)
            record[ch] = { 'start': start, 'length': length, 't': t, 'x': x }

        return record

    
    async def get_object(self, channels, length, to):
        return {}

    
                             
class ObjectTimeSeriesSource(TimeSeriesSource):
    def __init__(self, url, params):
        super().__init__(url, params)

        
    async def get_timeseries(self, channels, length, to):
        return {}

    
    async def get_object(self, channels, length, to):
        if self.channels is None:
            await self.scan_channels()
                    
        record = {}
        start = to - length

        for ch in channels:
            if ch not in self.channels:
                continue
            key = ch[0:len(ch)-len(self.suffix)]
            
            tsname = '%sindex_%s' % (objts_prefix, key)
            try:
                ts = await self.redis.ts().range(tsname, int(1000*start), int(1000*to))
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
                    obj = DataSource.decode_if_json(await self.redis.get(objname))
                except Exception as e:
                    logging.error('Redis: error on get(): %s: %s' % (ch, str(e)))
                    continue
            else:
                try:
                    obj = await self.redis.json().get(objname)
                except Exception as e:
                    logging.warning('Redis: error on json().get(): %s: %s' % (objname, str(e)))
                    continue

            record[ch] = {
                'start': start, 'length': length,
                't': math.floor(10*(tk/1000 - start))/10,
                'x': obj if obj is not None else {}
            }

        return record

    
    async def scan_channels(self):
        self.channels = {}
        if self.redis is None:
            return

        for key in await self.redis.keys():
            if not key.startswith(objts_prefix):
                continue
            if await self.redis.type(key) != 'TSDB-TYPE':
                continue
            name = key[len(objts_prefix+'index_'):]
            objtype, keytype = await self.find_object_type(name)
            if objtype is not None:
                self.channels[name+self.suffix] = { 'type': objtype }
                if keytype == 'string':
                    self.json_str_channels.add(name)
        

    async def find_object_type(self, name):
        tskey = objts_prefix + 'index_' + name
        try:
            tk, index = await self.redis.ts().get(tskey)
        except Exception as e:
            return None, None

        return await super().find_object_type('%s_%s_%d' % (objts_prefix, name, int(index)))
    
                    

class DataSource_Redis(DataSource):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)

        dburl = Schema.parse_dburl(params.get('url', ''))
        host = dburl.get('host', 'localhost')
        port = dburl.get('port', '6379')
        default_db = dburl.get('db', '0')

        def load_source(params, entrytype, SourceClass):
            source_list = []
            entry_list = params.get(entrytype, [])
            for entry in entry_list if type(entry_list) is list else [ entry_list ]:
                db = entry.get('db', default_db)
                url = f'redis://{host}:{port}/{db}'
                source_list.append(SourceClass(url, entry))
            return source_list
        
        self.kv_sources = load_source(params, 'key_value', KeyValueSource)
        self.obj_sources = load_source(params, 'object', ObjectSource)
        self.ts_sources = load_source(params, 'time_series', TimeSeriesSource)
        self.objts_sources =  load_source(params, 'object_time_series', ObjectTimeSeriesSource)
        self.sources = self.kv_sources + self.obj_sources + self.ts_sources + self.objts_sources
        
        if default_db is not None and len(self.sources) == 0:
            default_url = f'redis://{host}:{port}/{default_db}'
            self.kv_sources = [ KeyValueSource(default_url, {}) ]
            self.obj_sources = [ ObjectSource(default_url, {}) ]
            self.ts_sources = [ TimeSeriesSource(default_url, {}) ]
            self.objts_sources = [ ObjectTimeSeriesSource(default_url, {}) ]
            self.sources = self.kv_sources + self.obj_sources + self.ts_sources + self.objts_sources

            
    async def aio_initialize(self):
        for src in self.sources:
            await src.connect()
        
                    
    async def aio_finalize(self):
        for src in self.sources:
            await src.close()
        
                    
    async def aio_get_channels(self):
        for src in self.sources:
            await src.scan_channels()

        channels = []
        for src in self.sources:
            this_channels = await src.get_channels()
            channels.extend([ k for k in this_channels ])
            
        return channels

    
    async def aio_get_timeseries(self, channels, length, to, resampling=None, reducer='last', filler='fillna', envelope=0):
        record = {}
        for src in self.sources:
            record.update(await src.get_timeseries(channels, length, to))

        if resampling is None:
            return record
            
        return self.resample(record, length, to, resampling, reducer, filler, envelope)

                             
    async def aio_get_object(self, channels, length, to):
        record = {}
        for src in self.sources:
            record.update(await src.get_object(channels, length, to))

        return record
