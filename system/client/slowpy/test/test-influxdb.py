#! /usr/bin/env python3        


import slowpy as slp

datastore = slp.DataStore_InfluxDB2(
    url = 'influxdb2://sloworg:slowtoken@localhost:8087/SlowTestData',
    measurement = 'slowpy_ts'
)
datastore_objts = datastore.another(measurement='slowpy_objts')


dummy_device = slp.DummyWalkDevice()
histogram = slp.Histogram('test_histogram', 100, -10, 10)
graph = slp.Graph('test_graph', labels=['ch', 'value'])


while True:
    #histogram.clear()
    graph.clear()
    records = dummy_device.read()

    for record in records:
        datastore.write_timeseries(record['value'], tag='ch%02d' % record['channel'], timestamp=record['time'])
        histogram.fill(record["value"])
        graph.add_point(record["channel"], record["value"])

    datastore_objts.write_object_timeseries(histogram, name="test_histogram_ts")
    datastore_objts.write_object_timeseries(graph, name="test_graph_ts")
