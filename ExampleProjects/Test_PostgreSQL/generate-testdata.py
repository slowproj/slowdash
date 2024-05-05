#! /usr/bin/env python3        


import slowpy as slp
default_db_url = 'postgresql://postgres:postgres@localhost:5432/SlowStore'



def start(db_url):
    datastore = slp.DataStore_PostgreSQL(db_url)
    dummy_device = slp.DummyWalkDevice()
    while True:
        records = dummy_device.read()
        for record in records:
            datastore.write_timeseries(record['value'], tag='ch%02d'%record['channel'], timestamp=record['time'])

            

if __name__ == '__main__':
    from optparse import OptionParser
    optionparser = OptionParser()
    optionparser.add_option(
        '--db-url', action='store', dest='db_url', type='string', default=default_db_url,
        help='set Database URL, default is %s' % default_db_url
    )
    (options, args) = optionparser.parse_args()

    start(options.db_url)
