# Created by Sanshiro Enomoto on 3 June 2023 #


import sys, os, time, json, logging
from .datastore import DataStore


class DataStore_Redis(DataStore):
    use_redis_json = False
    
    def __init__(self, host, port, db, retention_length, time_bin_width=1):
        import redis

        self.host = host
        self.port = port
        self.db = db
        self.retention_length = retention_length
        self.time_bin_width = time_bin_width

        # retries up to 60 sec, for docker-compose etc.
        self.redis = None
        self.ts_set = set()
        for i in range(12):
            try:
                self.redis = redis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
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
            logging.error('Redis not loaded: %s:%s/%s' % (self.host, self.port, self.db))
            return
        
            
    def __del__(self):
        pass

    
    def another(self, db=None, retention_length=None, time_bin_width=None):
        if db is None:
            db = self.db
        if retention_length is None:
            retention_length = self.retention_length
        if time_bin_width is None:
            time_bin_width = self.time_bin_width

        return DataStore_Redis(self.host, self.port, db, retention_length, time_bin_width)
            

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
                    self.redis.ts().create(tag, retention_msecs=1000*self.retention_length)
                    self.ts_set.add(tag)
                except Exception as e:
                    logging.error('RedisTS.create(): %s' % str(e))
            self.redis.ts().add(tag, int(1000*timestamp), fields)
            
        else:
            for k, v in fields.items():
                ch = k if tag is None else "%s:%s" % (tag, k)
                if ch not in self.ts_set:
                    try:
                        self.redis.ts().create(ch, retention_msecs=1000*self.retention_length)
                        self.ts_set.add(ch)
                    except Exception as e:
                        logging.error('RedisTS.create(): %s' % str(e))
                self.redis.ts().add(ch, int(1000*timestamp), v)
                    
    
    def write_object(self, obj, name=None):
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
        
        if not self.redis.exists(name):
            try:
                self.redis.ts().create(name, retention_msecs=1000*self.retention_length)
            except Exception as e:
                logging.error('RedisTS.create(): %s' % str(e))
        if self.redis.type(name) != 'TSDB-TYPE':
            logging.error('TSDB-TYPE expected for %s in DB %s' % (name, self.db))
            return

        index = int((timestamp % self.retention_length) / self.time_bin_width)
        objname = '%s_%d' % (name, index)
        try:
            if self.use_redis_json:
                self.redis.json().set(objname, '$', obj.get())
            else:
                self.redis.set(objname, str(obj))
        except Exception as e:
            logging.error(e)
        try:
            self.redis.ts().add(name, int(1000*timestamp), index)
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
    
        
    def list_objects(self):
        obj_list = []
        for key in self.redis.keys():
            if self.redis.type(key) == 'ReJSON-RL':
                obj_list.append({ 'key': key })
        return obj_list
