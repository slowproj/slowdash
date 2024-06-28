#! /bin/env python3

couchdb_url = 'http://admin:neutrino@localhost:5984/photos'
design_name = 'SlowView'
series_name = 'RPiCamera'


import couchdb
db_url = couchdb_url.rsplit('/', 1)[0]
db_name = couchdb_url.rsplit('/', 1)[1]
couch = couchdb.Server(db_url)
db = couch[db_name]


def download(start, end):
    rows = db.view(f'{design_name}/{series_name}')[start:end].rows
    for row in rows:
        timestamp = row.key
        value = row.value.get(series_name)
        id = value.get('id', None).split('/')
        if id is None:
            continue
        doc_id, filename = id[0], id[1]

        doc = db.get(doc_id)
        if doc is None:
            continue
        att = db.get_attachment(doc, filename, default=None)
        if att is None:
            continue

        with open(filename, 'wb') as output:
            output.write(att.read())
        att.close()

        print(filename)



if __name__ == '__main__':
    from optparse import OptionParser
    optionparser = OptionParser()
    optionparser.add_option(
        '--length',
        action='store', dest='length', type='float', default=86400,
        help='length of the period to download, default 86400 (1 day)'
    )
    optionparser.add_option(
        '--to',
        action='store', dest='end', type='float', default=0,
        help='end time of the period, 0 for "now" (default), negative for the past in sec, or UNIX timestamp'
    )
    (options, args) = optionparser.parse_args()
    
    import time
    end = options.end
    if end <= 0:
        end += time.time()
    start = end - abs(options.length)
    
    download(start, end)
