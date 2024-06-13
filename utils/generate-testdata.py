#! /usr/bin/env python3        

import time
import numpy as np
import slowpy



stop_requested = False
import signal
def signal_handler(signum, frame):
    global stop_requested
    stop_requested = True
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


    
def start(db_url, ts_name='ts_data', obj_name='obj_data', objts_name='objts_data'):
    datastore = slowpy.datastore.create_datastore_from_url(db_url, ts_name, obj_name, objts_name)
    
    dummy_device = sld.DummyDevice_RandomWalk()
    readout_count = 0
    histogram = slowpy.Histogram('test_histogram', 100, -10, 10)
    graph = slowpy.Graph('test_graph', labels=['ch', 'value'])
    histogram2d = slowpy.Histogram2d('test_histogram2d', 10, 0, 10, 10, 0, 10)

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

        for channel in dummy_device.channels():
            t = time.time()
            value = dummy_device.read(channel)
            datastore.write_timeseries(value, tag='ch%02d'%channel, timestamp=t)
            histogram.fill(value)
            graph.add_point(channel, value)

        datastore.write_object(histogram)
        datastore.write_object(graph)

        datastore.write_object_timeseries(histogram, name='test_histogram_ts')
        datastore.write_object_timeseries(graph, name='test_graph_ts')
    
        for i in range(1000):
            x = np.random.normal(5, 2)
            y = np.random.normal(5, 3)
            histogram2d.fill(x, y)
        datastore.write_object(histogram2d)

        # Redis only
        if hasattr(datastore, 'write_hash'):
            datastore.write_hash('Status', {
                'Generator': __file__,
                'Count': readout_count
            })
        readout_count = readout_count + 1

            

if __name__ == '__main__':
    from optparse import OptionParser
    optionparser = OptionParser()
    optionparser.add_option(
        '--db-url', action='store', dest='db_url', type='string', default='dump:///',
        help='set Database URL'
    )
    (options, args) = optionparser.parse_args()

    start(options.db_url)
