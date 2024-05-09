# Created by Sanshiro Enomoto on 3 June 2023 #


import sys, os, time, json, logging
from .datastore import DataStore

objts_prefix = '__sd_objts'


class DataStore_Redis(DataStore):
    def __init__(self, url, retention_length=None, objts_retention_length=3600, objts_timebin=1):
        self.url = url
        self.retention_length = retention_length
        self.objts_retention_length = objts_retention_length
        self.objts_timebin = objts_timebin
        self.use_redis_json = False

        # retries up to 60 sec, for docker-compose etc.
        import redis
        self.redis = None
        self.ts_set = set()
        for i in range(12):
            try:
                self.redis = redis.from_url(self.url, decode_responses=True)
                for key in self.redis.keys():
                    if self.redis.type(key) == 'TSDB-TYPE':
                        self.ts_set.add(key)
                break
            except Exception as e:
                logging.info(e)
                logging.info('Redis not connected: retry in 5 sec')
                time.sleep(5)
        else:
            self.redis = None
        
        if self.redis is None:
            logging.error('Redis not loaded: %s' % self.url)
            return
        
                
    def __del__(self):
        pass

    
    def write_timeseries(self, fields, tag=None, timestamp=None):
        if self.redis is None:
            return
        if timestamp is None:
            timestamp = time.time()

        if not isinstance(fields, dict):
            if tag is None:
                return
            if tag not in self.ts_set:
                try:
                    if self.retention_length is None:
                        self.redis.ts().create(tag)
                    else:
                        self.redis.ts().create(tag, retention_msecs=1000*self.retention_length)
                    self.ts_set.add(tag)
                except Exception as e:
                    logging.error('RedisTS.create(): %s' % str(e))
            if tag in self.ts_set:
                self.redis.ts().add(tag, int(1000*timestamp), fields)
            
        else:
            for k, v in fields.items():
                ch = k if tag is None else "%s:%s" % (tag, k)
                if ch not in self.ts_set:
                    try:
                        if self.retention_length is None:
                            self.redis.ts().create(ch)
                        else:
                            self.redis.ts().create(ch, retention_msecs=1000*self.retention_length)
                        self.ts_set.add(ch)
                    except Exception as e:
                        logging.error('RedisTS.create(): %s' % str(e))
                if ch in self.ts_set:
                    self.redis.ts().add(ch, int(1000*timestamp), v)
                    
    
    def write_object(self, obj, name=None):
        if self.redis is None:
            return
        if name is None:
            name = obj.name
            
        try:
            if self.use_redis_json:
                self.redis.json().set(name, '$', obj.get())     
            else:
                self.redis.set(name, str(obj))                  
        except Exception as e:
            logging.error(e)
        

    def write_object_timeseries(self, obj, timestamp=None, name=None):
        if self.redis is None:
            return
        
        if timestamp is None:
            timestamp = time.time()
        if name is None:
            name = obj.name

        tsname = '%sindex_%s' % (objts_prefix, name)
        if not self.redis.exists(tsname):
            try:
                self.redis.ts().create(tsname, retention_msecs=1000*self.objts_retention_length)
            except Exception as e:
                logging.error('RedisTS.create(): %s' % str(e))
        if self.redis.type(tsname) != 'TSDB-TYPE':
            logging.error('TSDB-TYPE expected for %s in DB %s' % (tsname, self.db))
            return

        index = int((timestamp % self.objts_retention_length) / self.objts_timebin)
        objname = '%s_%s_%d' % (objts_prefix, name, int(index))
        try:
            if self.use_redis_json:
                self.redis.json().set(objname, '$', obj.get())
            else:
                self.redis.set(objname, str(obj))
        except Exception as e:
            logging.error(e)
        try:
            self.redis.ts().add(tsname, int(1000*timestamp), index)
        except Exception as e:
            logging.error(e)

            
    ### Redis specific methods ###
    
    def write_hash(self, name, record):
        try:
            self.redis.hset(name, mapping=record)
        except Exception as e:
            logging.error(e)

            
    def flush_db(self):
        # this deletes all the contents in the DB
        self.redis.flushdb()
        self.ts_set = set()

            
    def list_timeseries(self):
        obj_list = []
        for key in self.redis.keys():
            if self.redis.type(key) == 'TSDB-TYPE':
                info = self.redis.ts().info(key)
                obj_list.append({
                    'key': key,
                    'totalSamples': info.total_samples,
                    'firstTimeStamp': info.first_time_stamp,
                    'lastTimeStamp': info.last_time_stamp,
                    'retentionTime': info.retention_msecs
                })
        return obj_list
    
        
    def list_json(self):
        obj_list = []
        for key in self.redis.keys():
            if self.redis.type(key) == 'ReJSON-RL':
                obj_list.append({ 'key': key })
        return obj_list
