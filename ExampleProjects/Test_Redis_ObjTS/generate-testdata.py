#! /usr/bin/env python3        


import slowpy as slp
default_db_url = 'redis://localhost:6379/1'


def start(db_url):
    datastore = slp.DataStore_Redis(db_url, retention_length=3600)
    datastore_objts = datastore.another(db=2)
    
    dummy_device = slp.DummyWalkDevice()
    count = 0
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

            datastore.write_object(histogram)
            datastore.write_object(graph)

            datastore_objts.write_object_timeseries(histogram, name="test_histogram_02")
            datastore_objts.write_object_timeseries(graph, name="test_graph_02")
    
            datastore.write_hash('Status', {
                'Generator': __file__,
                'Count': count
            })
            count = count + 1

            

if __name__ == '__main__':
    from optparse import OptionParser
    optionparser = OptionParser()
    optionparser.add_option(
        '--db-url', action='store', dest='db_url', type='string', default=default_db_url,
        help='set Database URL, default is %s' % default_db_url
    )
    (options, args) = optionparser.parse_args()

    start(options.db_url)
