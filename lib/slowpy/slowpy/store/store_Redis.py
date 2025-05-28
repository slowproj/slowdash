# Created by Sanshiro Enomoto on 3 June 2023 #


import sys, os, time, json, logging
from .store import DataStore

objts_prefix = '__sd_objts'


class DataStore_Redis(DataStore):
    def __init__(self, db_url='redis://localhost/1', retention_length=None, objts_retention_length=3600, objts_timebin=1):
        self.db_url = db_url
        self.retention_length = retention_length
        self.objts_retention_length = objts_retention_length
        self.objts_timebin = objts_timebin

        # retries up to 60 sec, for docker-compose etc.
        import redis
        self.redis = None
        self.ts_set = set()
        for i in range(12):
            try:
                self.redis = redis.from_url(self.db_url, decode_responses=True)
                for key in self.redis.keys():
                    if self.redis.type(key) == 'TSDB-TYPE':
                        self.ts_set.add(key)
                break
            except Exception as e:
                logging.info(e)
                logging.warn('Redis not connected: retry in 5 sec')
                time.sleep(5)
        else:
            self.redis = None
        
        if self.redis is None:
            logging.error('Redis not loaded: %s' % self.db_url)
            return
        
                
    def __del__(self):
        pass


    def another(self, db=None, retention_length=0, objts_retention_length=0, objts_timebin=0):
        if db is not None:
            db_url = self.db_url.rsplit('/', 1)[0] + f'/{db}'
        else:
            db_url = self.db_url

        if retention_length == 0:
            retention_length = self.retention_length
        if objts_retention_length == 0:
            objts_retention_length = self.objts_retention_length
        if objts_timebin == 0:
            objts_timebin = self.objts_timebin

        return DataStore_Redis(db_url, retention_length, objts_retention_length, objts_timebin)

    
    def _open_transaction(self):
        return self.redis

    
    def _close_transaction(self, redis):
        pass

    
    def _write_one(self, redis, timestamp, tag, fields, values, update):
        channels = self._channels(tag, fields)
        for i in range(min(len(channels), len(values))):
            if update is True:
                self.write_element(channel=channels[i], value=values[i])
            elif type(values[i]) in [ int, float ]:
                self.write_timeseries(timestamp, channel=channels[i], value=values[i])
            else:
                self.write_object_timeseries(timestamp, channel=channels[i], value=values[i])

        
    ### Redis specific implementations ###
    
    def write_element(self, channel, value):
        try:
            self.redis.set(channel, str(value))
        except Exception as e:
            logging.error('RedisTS.set(): %s' % str(e))
            
        
    def write_timeseries(self, timestamp, channel, value):
        if channel not in self.ts_set:
            try:
                if self.retention_length is None:
                    self.redis.ts().create(channel)
                else:
                    self.redis.ts().create(channel, retention_msecs=1000*self.retention_length)
                self.ts_set.add(channel)
            except Exception as e:
                logging.error('RedisTS.create(): %s' % str(e))
                
        if channel in self.ts_set:
            self.redis.ts().add(channel, int(1000*timestamp), value)
                    
    
    def write_object_timeseries(self, timestamp, channel, value):
        tsname = '%sindex_%s' % (objts_prefix, channel)
        if not self.redis.exists(tsname):
            try:
                self.redis.ts().create(tsname, retention_msecs=1000*self.objts_retention_length)
            except Exception as e:
                logging.error('RedisTS.create(): %s' % str(e))
        if self.redis.type(tsname) != 'TSDB-TYPE':
            logging.error('TSDB-TYPE expected for %s in DB %s' % (tsname, self.db))
            return

        index = int((timestamp % self.objts_retention_length) / self.objts_timebin)
        objname = '%s_%s_%d' % (objts_prefix, channel, int(index))
        try:
            self.redis.set(objname, str(value))
        except Exception as e:
            logging.error(e)
        try:
            self.redis.ts().add(tsname, int(1000*timestamp), index)
        except Exception as e:
            logging.error(e)

            
    ### Redis specific methods ###
    
    def flush_db(self):
        # this deletes all the contents in the DB
        self.redis.flushdb()
        self.ts_set = set()

            
    def write_hash(self, name, record):
        try:
            self.redis.hset(name, mapping=record)
        except Exception as e:
            logging.error(e)

            
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
