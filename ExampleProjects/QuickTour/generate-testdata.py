#! /usr/bin/env python3


name = 'QuickTourTestData'
table_name = 'testdata'
schema = '(datetime DATETIME, timestamp INTEGER, channel STRING, value REAL, PRIMARY KEY(timestamp, channel))'

obj_table_name = 'testdata_obj'
obj_schema = '(datetime DATETIME, timestamp INTEGER, channel STRING, value STRING, PRIMARY KEY(timestamp, channel))'


import sys, os, time, json
import logging
logger = logging.getLogger(name)
logger.addHandler(logging.StreamHandler(sys.stderr))
logger.setLevel(logging.INFO)



##### Data Objects (copy from SlowPy) #####


class HistogramScale:
    def __init__(self, nbins, range_min, range_max):
        self.nbins = max(nbins, 0)
        self.min = min(range_min, range_max)
        self.max = max(range_min, range_max)
        if not (self.min < self.max):
            self.nbins = 0
        elif self.nbins > 0:
            self.bin_width = (self.max - self.min) / self.nbins

    def get_bin_of(self, value):
        if self.nbins <= 0 or value < self.min or value >= self.max:
            return None
        return int((value - self.min) / self.bin_width)
        
    def get_bin_range_of(self, bin_index):
        if self.nbins <= 0:
            return (None, None)
        left = self.min + bin_index * self.bin_width
        right = left + self.bin_width
        return (left, right)
    
    
class Histogram:
    def __init__(self, name, nbins, range_min, range_max):
        self.name = name
        self.scale = HistogramScale(nbins, range_min, range_max)
        if self.scale.nbins > 0:
            self.counts = np.zeros(self.scale.nbins)
        else:
            self.counts = []

    def clear(self):
        self.counts[:] = 0

    def fill(self, value, weight=1):
        bin = self.scale.get_bin_of(value)
        if bin is not None:
            self.counts[bin] += weight

    def rebin(self, nbins, range_min, range_max):
        if nbins <= 0:
            return
        new_scale = HistogramScale(nbins, range_min, range_max)
        new_counts = np.zeros(new_scale.nbins)
        for bin in range(self.scale.nbins):
            (left, right) = self.scale.get_bin_range_of(bin)
            for k in range(int(self.counts[bin])):
                value = np.random.uniform(left, right)
                new_bin = new_scale.get_bin_of(value)
                if new_bin is not None:
                    new_counts[new_bin] += 1
        self.scale = new_scale
        self.counts = new_counts

    def get(self):
        return {
            'bins': { 'min': self.scale.min, 'max': self.scale.max },
            'counts': self.counts.tolist()
        }

    def __str__(self):
        return json.dumps(self.get())

    
    
class Graph:
    def __init__(self, name):
        self.name = name
        self.clear()

    def clear(self):
        self.x = []
        self.y = []
        
    def add_point(self, x, y):
        self.x.append(x)
        self.y.append(y)
    
    def get(self):
        return {
            'x': self.x,
            'y': self.y
        }
        
    def __str__(self):
        return json.dumps(self.get())



##### SQLite Data Store (copy from SlowPy) #####


class DataStore_SQLite:
    def __init__(self, db_name, table_name, obj_table_name=None):
        self.db_name = db_name        
        self.table_name = table_name
        self.obj_table_name = obj_table_name

        self.conn = None
        
        import sqlite3
        if not os.path.exists('%s.db' % self.db_name):
            logger.info('DB file "%s.db" does not exist. Creating...' % self.db_name)
        self.conn = sqlite3.connect('%s.db' % self.db_name)
        logger.info('DB "%s" is connnected.' % self.db_name)

        cur = self.conn.cursor()
        cur.execute('select name from sqlite_master where type="table"')
        table_list = [ table_name[0] for table_name in cur.fetchall() ]
        if self.table_name is not None and self.table_name not in table_list:
            logger.info('Creating a new time-series data table "%s"...' % self.table_name)
            cur.execute('CREATE TABLE %s%s' % (self.table_name, schema))
            self.conn.commit()
        if self.obj_table_name is not None and self.obj_table_name not in table_list:
            logger.info('Creating a new object-timeseries data table "%s"...' % self.obj_table_name)
            cur.execute('CREATE TABLE %s%s' % (self.obj_table_name, obj_schema))
            self.conn.commit()

            
    def __del__(self):
        if self.conn is not None:
            self.conn.close()
            logger.info('DB "%s" is disconnnected.' % self.db_name)


    def write_timeseries(self, fields, tag=None, timestamp=None):
        if self.conn is None:
            return
        cur = self.conn.cursor()
        
        if timestamp is None:
            timestamp = time.time()

        if not isinstance(fields, dict):
            if tag is None:
                return
            cur.execute('INSERT INTO %s VALUES(CURRENT_TIMESTAMP,%d,"%s",%f)' % (self.table_name, timestamp, tag, fields))
        else:
            for k, v in fields.items():
                ch = k if tag is None else "%s:%s" % (tag, k)
                cur.execute('INSERT INTO %s VALUES(CURRENT_TIMESTAMP,%d,"%s",%f)' % (self.table_name, timestamp, ch, v))
        self.conn.commit()
                    
    
    def write_object_timeseries(self, obj, timestamp=None):
        if self.conn is None:
            return
        if self.obj_table_name is None:
            return
        
        if timestamp is None:
            timestamp = time.time()
        
        cur = self.conn.cursor()
        cur.execute(
            '''INSERT INTO %s VALUES(CURRENT_TIMESTAMP,%d,'%s','%s')''' %
            (self.obj_table_name, timestamp, obj.name, str(obj))
        )
        self.conn.commit()

    
##### Dummy Data Source #####

import numpy as np

class DummyWalkDevice:
    def __init__(self, n=16, decay=0.1, walk=1.0):
        self.n = n
        self.decay = decay
        self.walk = walk
        
        self.x = [0] * n
        for ch in range(self.n):
            self.x[ch] = np.random.normal(0, 10*self.walk)

        
    def read(self):
        t = int(time.time())
        for ch in range(self.n):
            self.x[ch] = (1-self.decay) * self.x[ch] + np.random.normal(0, self.walk)
        return [ { "time": t, "channel": ch, "value": self.x[ch] } for ch in range(self.n) ]


    
##### Run-Loop Thread and Start / Stop #####

import signal, threading
current_thread = None
stop_requested = False
    
def run(params):
    histogram_name = params.get('histogram_name', '')
    graph_name = params.get('graph_name', '')
    
    device = DummyWalkDevice(n=16, decay=0.1, walk=1.0)
    if len(histogram_name) == 0 and len(graph_name) == 0:
        datastore = DataStore_SQLite(name, table_name)
    else:
        datastore = DataStore_SQLite(name, table_name, obj_table_name)
    logger.info('Start')

    
    histogram = Histogram(histogram_name, 20, -10, 10) if len(histogram_name) > 0 else None
    graph = Graph(graph_name) if len(graph_name) > 0 else None
    
    event_count = 0
    while not stop_requested:
        records = device.read()
        timestamp = records[0]["time"]
        
        for data in records:
            datastore.write_timeseries(data['value'], tag='ch%02d' % data['channel'], timestamp=data['time'])

        if histogram is not None:
            histogram.clear()
            for record in records:
                histogram.fill(record["value"])
            datastore.write_object_timeseries(histogram, timestamp)
            
        if graph is not None:
            graph.clear()
            for record in records:
                graph.add_point(record["channel"], record["value"])
            datastore.write_object_timeseries(graph, timestamp)
            
        event_count = event_count + 1
        time.sleep(1)

    logger.info('Stop: %d events processed.' % event_count)
    
    
def start(params):
    global current_thread
    if current_thread is None:
        current_thread = threading.Thread(target=run, args=(params,))
        current_thread.start()

    
def stop(signum=None, frame=None):
    global current_thread, stop_requested
    if current_thread is not None:
        stop_requested = True
        logger.info('stop requested. Wait a second...')
        current_thread.join()
        current_thread = None
        logger.info('stop completed.')


        
##### User Module Interface #####
        
def initialize(params):
    start(params)

    
def finalize():
    stop()
    


##### Standalone Execution #####
    
if __name__ == '__main__':
    from optparse import OptionParser
    optionparser = OptionParser()
    optionparser.add_option(
        '--histogram',
        action='store', dest='histogram_name', type='string', default="",
        help='generate time-series of histograms'
    )
    optionparser.add_option(
        '--graph',
        action='store', dest='graph_name', type='string', default="",
        help='generate time-series of graphs'
    )
    (options, args) = optionparser.parse_args()
    opts = {
        'histogram_name': options.histogram_name,
        'graph_name': options.graph_name
    }
    
    signal.signal(signal.SIGINT, stop)
    start(opts)
