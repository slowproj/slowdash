#! /usr/bin/env python3        


import numpy as np
import slowpy as slp


datastore = slp.DataStore_PostgreSQL('postgresql://postgres:postgres@localhost:5432/SlowStore')

histogram = slp.Histogram('test_histogram_01', 20, -10, 10)
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

    histogram.add_attr('color', readout_count)
    graph.add_attr('color', readout_count+1)

    
    records = dummy_device.read()
    
    for record in records:
        datastore.write_timeseries(record['value'], tag='ch%02d'%record['channel'], timestamp=record['time'])
        histogram.fill(record["value"])
        graph.add_point(record["channel"], record["value"])

    datastore.write_object(histogram)
    datastore.write_object(graph)

    datastore.write_object_timeseries(histogram, name="test_histogram_02")
    datastore.write_object_timeseries(graph, name="test_graph_02")

    for i in range(1000):
        x = np.random.normal(5, 2)
        y = np.random.normal(5, 3)
        histogram2d.fill(x, y)
    datastore.write_object(histogram2d)
    
    readout_count = readout_count + 1
