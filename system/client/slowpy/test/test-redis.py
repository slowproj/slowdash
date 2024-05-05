#! /usr/bin/env python3        


import slowpy as slp

datastore = slp.DataStore_Redis('redis://localhost:6379/1', retention_length=3600)
datastore_objts = datastore.another(db=2)

#slp.DataStore_Redis.use_redis_json = True
#datastore.flush_db()
#datastore_objts.flush_db()



histogram = slp.Histogram('test_histogram_01', 100, -10, 10)
graph = slp.Graph('test_graph_01', labels=['ch', 'value'])

dummy_device = slp.DummyWalkDevice()
count = 0


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
    
    datastore.write_hash('Status', {
        'Generator': __file__,
        'Count': count
    })
    count = count + 1
    
    print(datastore.list_objects())
    print(datastore.list_timeseries())
    print(datastore_objts.list_timeseries())
    
