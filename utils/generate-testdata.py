#! /usr/bin/env python3        


import numpy as np
import slowpy as slp
default_db_url = 'sqlite:///SlowTestData'


def start(db_url, ts_name='ts_data', obj_name='obj_data', objts_name='objts_data'):
    datastore = slp.create_datastore_from_url(db_url, ts_name, obj_name, objts_name)
    
    dummy_device = slp.DummyWalkDevice()
    readout_count = 0
    histogram = slp.Histogram('test_histogram', 100, -10, 10)
    graph = slp.Graph('test_graph', labels=['ch', 'value'])
    histogram2d = slp.Histogram2d('test_histogram2d', 10, 0, 10, 10, 0, 10)

    histogram.add_stat(slp.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))
    histogram.add_stat(slp.HistogramCountStat(-5.2, 5.2))
    histogram.add_stat(slp.HistogramCountStat(0, 10))
    histogram2d.add_stat(slp.Histogram2dBasicStat())
    graph.add_stat(slp.GraphYStat(['Entries', 'Y-Mean', 'Y-RMS'], ndigits=3))

    histogram.add_attr('title', "test title")
    histogram.add_attr('xtitle', "test x-title")
    histogram.add_attr('ytitle', "test y-title")


    while True:
        #histogram.clear()
        graph.clear()
        histogram.add_attr('color', readout_count)
        graph.add_attr('color', readout_count+1)
    
        records = dummy_device.read()
    
        for record in records:
            datastore.write_timeseries(record['value'], tag='ch%02d' % record['channel'], timestamp=record['time'])
            histogram.fill(record["value"])
            graph.add_point(record["channel"], record["value"])

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
        '--db-url', action='store', dest='db_url', type='string', default=default_db_url,
        help='set Database URL, default is %s' % default_db_url
    )
    (options, args) = optionparser.parse_args()

    start(options.db_url)
