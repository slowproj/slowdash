# Created by Sanshiro Enomoto on 3 June 2023 #


import sys, os, time, json, logging
from .datastore import DataStore


class DataStore_Redis3(DataStore):
    def __init__(self, host, port, db, retention_length, time_bin_width=1):
        import rejson
        from redistimeseries.client import Client as RedisTimeSeries

        self.host = host
        self.port = port
        self.db = db
        self.retention_length = retention_length
        self.time_bin_width = time_bin_width

        self.redis_ts = None
        self.redis_json = None
        try:
            self.redis_ts = RedisTimeSeries(host=self.host, port=self.port, db=self.db, decode_responses=True)
            self.redis_json = rejson.Client(host=self.host, port=self.port, db=self.db, decode_responses=True)
        except Exception as e:
            logging.error(e)
            return
        
        if self.redis_ts is None:
            logging.error('RedisTS not loaded: %s:%s/%s' % (self.host, self.port, self.db))
        if self.redis_json is None:
            logging.error('RedisJSON not loaded: %s:%s/%s' % (self.host, self.port, self.db))

        self.ts_set = set()
        for key in self.redis_json.keys():
            if self.redis_json.type(key) == 'TSDB-TYPE':
                self.ts_set.add(key)
        
            
    def __del__(self):
        pass

    
    def write_timeseries(self, fields, tag=None, timestamp=None):
        if self.redis_ts is None:
            return
        if timestamp is None:
            timestamp = time.time()

        if not isinstance(fields, dict):
            if tag is None:
                return
            if tag not in self.ts_set:
                try:
                    self.redis_ts.create(tag, retention_msecs=1000*self.retention_length)
                    self.ts_set.add(tag)
                except Exception as e:
                    logging.error('RedisTS.create(): %s' % str(e))
            self.redis_ts.add(tag, int(1000*timestamp), fields)
            
        else:
            for k, v in fields.items():
                ch = k if tag is None else "%s:%s" % (tag, k)
                if ch not in self.ts_set:
                    try:
                        self.redis_ts.create(ch, retention_msecs=1000*self.retention_length)
                        self.ts_set.add(ch)
                    except Exception as e:
                        logging.error('RedisTS.create(): %s' % str(e))
                self.redis_ts.add(ch, int(1000*timestamp), v)
                    
    
    def write_object(self, obj, name=None):
        if name is None:
            name = obj.name
            
        try:
            self.redis_json.jsonset(name, '$', obj.get())
        except Exception as e:
            logging.error(e)
        

    def write_object_timeseries(self, obj, timestamp=None, name=None):
        if self.redis_ts is None or self.redis_json is None:
            return
        
        if timestamp is None:
            timestamp = time.time()
        if name is None:
            name = obj.name
        
        if not self.redis_json.exists(name):
            try:
                self.redis_ts.create(name, retention_msecs=1000*self.retention_length)
            except Exception as e:
                logging.error('RedisTS.create(): %s' % str(e))
        if self.redis_json.type(name) != 'TSDB-TYPE':
            logging.error('TSDB-TYPE expected for %s in DB %s' % (name, self.db))
            return

        index = int((timestamp % self.retention_length) / self.time_bin_width)
        objname = '%s_%d' % (name, index)
        try:
            self.redis_json.jsonset(objname, '$', obj.get())
        except Exception as e:
            logging.error(e)
        try:
            self.redis_ts.add(name, int(1000*timestamp), index)
        except Exception as e:
            logging.error(e)

            
    ### Redis specific methods ###
    
    def write_hash(self, name, record):
        try:
            self.redis_json.hset(name, mapping=record)
        except Exception as e:
            logging.error(e)

            
    def flush_db(self):
        # this deletes all the contents in the DB
        self.redis_json.flushdb()
        self.ts_set = set()

            
    def list_timeseries(self):
        obj_list = []
        for key in self.redis_json.keys():
            if self.redis_json.type(key) == 'TSDB-TYPE':
                info = self.redis_ts.info(key)
                obj_list.append({
                    'key': key,
                    'totalSamples': info.total_samples,
                    'firstTimeStamp': info.first_time_stamp,
                    'lastTimeStamp': info.last_time_stamp,
                    'retentionTime': info.retention_msecs
                })
        return obj_list
    
        
    def list_objects(self):
        obj_list = []
        for key in self.redis_json.keys():
            if self.redis_json.type(key) == 'ReJSON-RL':
                obj_list.append({ 'key': key })
        return obj_list
