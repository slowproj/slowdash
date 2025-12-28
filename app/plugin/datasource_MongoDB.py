# Created by Sanshiro Enomoto on 4 June 2022 #


import sys, os, time, logging
from sd_datasource import DataSource

import pymongo


class DataSource_MongoDB(DataSource):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        self.db = None
        self.collection = None
        host = params.get('host', 'localhost')
        port = params.get('port', 27017)
        
        self.db_name = params.get('db', None)
        self.collection_name = params.get('collection', None)
        if self.db_name is None or self.collection_name is None:
            logging.error('No DB and Collection names are given')
            return
            
        self.time_field = params.get('time_field', None)
        if self.time_field is None:
            logging.error('Not time-field name is given')
            return
        
        try:
            self.client = pymongo.MongoClient(host, port)
        except Exception as e:
            sys.stderr.write('ERROR: unable to connect MongoDB server: %s\n' % e)
            sys.stderr.write('mongod host: %s, port %s\n' % (host, port))
            return

        try:
            self.db = self.client[self.db_name]
        except:
            sys.stderr.write('ERROR: unable to find DB: %s\n' % self.db_name)
            return
        try:
            self.collection = self.db[self.collection_name]
        except:
            sys.stderr.write('ERROR: unable to find Collection: %s\n' % self.collection_name)
            
            
    def get_channels(self):
        if self.collection is None:
            return None

        to = time.time()
        start = to - 30*86400
        query = { "$and": [
            {self.time_field: {"$gte": start }},
            {self.time_field: {"$lt": to }}
        ]}

        # TODO...: make this more efficient
        channel_set = set()
        for record in self.collection.find(query, {"_id": 0}):
            for key in record.keys():
                if key not in channel_set:
                    channel_set.add(key)
                    
        return [ {'name': name} for name in sorted(channel_set) ]
    
    
    def get_timeseries(self, channels, length, to, resampling=None, reducer='last', filler='fillna', envelope=0):
        if self.collection is None:
            return None

        start = int(float(to) - float(length))
        query = { "$and": [
            {self.time_field: {"$gte": start }},
            {self.time_field: {"$lt": int(to) }}
        ]}

        fields = {'_id': 0, self.time_field: 1}
        for field in channels:
            fields[field] = 1
    
        cursor = self.collection.find(query, fields)
        
        result = {}
        for doc in cursor.sort(self.time_field, pymongo.ASCENDING):
            time = doc[self.time_field]
            for channel in doc.keys():
                if channel == self.time_field:
                    continue
                if channel not in result:
                    result[channel] = {
                        'start': start, 'length': int(length), 't': [], 'x': []
                    }
                try:
                    t, x = int(1000*(time-start))/1000.0, float(doc[channel])
                    if x >= 0 or x < 0:
                        result[channel]['t'].append(t)
                        result[channel]['x'].append(x)
                except:
                    pass
                    
        if resampling is not None:
            return self.resample(result, length, to, resampling, reducer, filler, envelope)
        else:
            return result
