#! /usr/bin/env python3        


import numpy as np
import slowpy as slp


datastore = slp.DataStore_Redis('redis://localhost:6379/1', retention_length=3600)
datastore_objts = datastore.another(db=2)

#slp.DataStore_Redis.use_redis_json = True
#datastore.flush_db()
#datastore_objts.flush_db()


histogram = slp.Histogram('test_histogram_01', 100, -10, 10)
graph = slp.Graph('test_graph_01', labels=['ch', 'value'])
histogram2d = slp.Histogram2d('test_histogram2d_00', 10, 0, 10, 10, 0, 10)

histogram.add_stat(slp.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))
histogram.add_stat(slp.HistogramCountStat(-5.2, 5.2))
histogram.add_stat(slp.HistogramCountStat(0, 10))
histogram2d.add_stat(slp.Histogram2dBasicStat())
graph.add_stat(slp.GraphYStat(['Entries', 'Y-Mean', 'Y-RMS'], ndigits=3))

histogram.add_attr('title', "test title")
histogram.add_attr('xtitle', "test x-title")
histogram.add_attr('ytitle', "test y-title")


dummy_device = slp.DummyWalkDevice()
readout_count = 0


while True:
    #histogram.clear()
    graph.clear()
    
    records = dummy_device.read()
    
    for record in records:
        datastore.write_timeseries(record['value'], tag='ch%02d' % record['channel'], timestamp=record['time'])
        histogram.fill(record["value"])
        graph.add_point(record["channel"], record["value"])

    datastore.write_object(histogram)
    datastore.write_object(graph)

    datastore_objts.write_object_timeseries(histogram, name="test_histogram_02")
    datastore_objts.write_object_timeseries(graph, name="test_graph_02")
    
    for i in range(1000):
        x = np.random.normal(5, 2)
        y = np.random.normal(5, 3)
        histogram2d.fill(x, y)
    datastore.write_object(histogram2d)
    
    datastore.write_hash('Status', {
        'Generator': __file__,
        'Count': readout_count
    })
    readout_count = readout_count + 1
    
    print(datastore.list_objects())
    print(datastore.list_timeseries())
    print(datastore_objts.list_timeseries())
    
