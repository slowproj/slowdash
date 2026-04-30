#! /usr/bin/env python3        

import time, logging
import numpy as np
import slowpy
from slowpy.control import RandomWalkDevice



stop_requested = False
import signal
def signal_handler(signum, frame):
    global stop_requested
    stop_requested = True
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


    
def start(db_url, ts_name='ts_data', obj_name='obj_data', objts_name='objts_data', *, interval=1.0):
    datastore_ts = slowpy.store.create_datastore_from_url(db_url, ts_name)
    datastore_obj = slowpy.store.create_datastore_from_url(db_url, obj_name)
    datastore_objts = slowpy.store.create_datastore_from_url(db_url, objts_name)

    device = RandomWalkDevice()
    readout_count = 0
    histogram = slowpy.Histogram(100, -10, 10)
    graph = slowpy.Graph(labels=['ch', 'value'])
    histogram2d = slowpy.Histogram2d(10, 0, 10, 10, 0, 10)

    histogram.add_stat(slowpy.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))
    histogram.add_stat(slowpy.HistogramCountStat(-5.2, 5.2))
    histogram.add_stat(slowpy.HistogramCountStat(0, 10))
    histogram2d.add_stat(slowpy.Histogram2dBasicStat())
    graph.add_stat(slowpy.GraphYStat(['Entries', 'Y-Mean', 'Y-RMS'], ndigits=3))

    histogram.add_attr('title', "test title")
    histogram.add_attr('xtitle', "test x-title")
    histogram.add_attr('ytitle', "test y-title")


    while not stop_requested:
        #histogram.clear()
        graph.clear()
        histogram.add_attr('color', readout_count)
        graph.add_attr('color', readout_count+1)

        for channel in device.channels():
            t = time.time()
            value = device.read(channel)
            datastore_ts.append(value, tag='ch%02d'%channel, timestamp=t)
            histogram.fill(value)
            graph.add_point(channel, value)

        datastore_obj.update(histogram, tag='test_histogram')
        datastore_obj.update(graph, tag='test_graph')

        datastore_objts.append(histogram, tag='test_histogram_ts')
        datastore_objts.append(graph, tag='test_graph_ts')
    
        for i in range(1000):
            x = np.random.normal(5, 2)
            y = np.random.normal(5, 3)
            histogram2d.fill(x, y)
        datastore_obj.update(histogram2d, tag='test_histogram2d')

        # Redis only
        if hasattr(datastore_obj, 'write_hash'):
            datastore_obj.write_hash('Status', {
                'Generator': __file__,
                'Count': readout_count
            })
        readout_count = readout_count + 1

        time.sleep(interval)

        

if __name__ == '__main__':
    from optparse import OptionParser
    optionparser = OptionParser()
    optionparser.add_option(
        '--db-url', action='store', dest='db_url', type='string', default='dump:///',
        help='set Database URL'
    )
    optionparser.add_option(
        '--interval', action='store', dest='interval', type='float', default=1.0,
        help='data readout inteval'
    )
    optionparser.add_option(
        '--logging', action='store', dest='loglevel', default='info', choices=['debug', 'info', 'warning', 'error'],
        help='logging level'
    )
    (options, args) = optionparser.parse_args()

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        level=getattr(logging, options.loglevel.upper(), logging.INFO),
        format='%(asctime)s %(levelname)s: %(filename)s %(funcName)s():   %(message)s', 
        datefmt='%y-%m-%d %H:%M:%S'
    )
    
    start(options.db_url, interval=options.interval)
