#! /usr/bin/env python3        


import slowpy as slp

datastore = slp.DataStore_InfluxDB(
    url = 'http://localhost:8086',
    org = 'SlowDash',
    token = 'TCr7R5dupugRMAQL_r_dXf_bXO5vgScMMee3ZMu8WbMAsz07GvsHwQJoCv85JnBW58BAs6REJuOKAS_8tfTp6w==',
    bucket = 'TestData',
    measurement = 'TestTimeSeries'
)
datastore_obj = datastore.another(measurement='TestTimeSeriesOfObjects')


dummy_device = slp.DummyWalkDevice()
histogram = slp.Histogram('test_histogram_01', 100, -10, 10)
graph = slp.Graph('test_graph_01', labels=['ch', 'value'])


while True:
    #histogram.clear()
    graph.clear()
    records = dummy_device.read()

    for record in records:
        datastore.write_timeseries(record['value'], tag='ch%02d' % record['channel'], timestamp=record['time'])
        histogram.fill(record["value"])
        graph.add_point(record["channel"], record["value"])

    datastore_obj.write_object_timeseries(histogram, name="test_histogram_02")
    datastore_obj.write_object_timeseries(graph, name="test_graph_02")
