
'''Posting data records via HTTP-POST
- command-line example:
  - curl -X POST 'http://localhost:18881/api/postdata' --data '{"ch0":123}'
  - curl -X POST 'http://localhost:18881/api/postdata?timestamp=TIMESTAMP' --data '{"ch0":123}'
- TIMESTAMP is UNIX timestamp, 0 for "now" (default), negative N for "past N seconds"
- data is a JSON string for { channel: value, ... }
'''


import slowpy, slowlette
webapi = slowlette.Slowlette()
datastore = None


def _initialize(params):
    global datastore
    db_url = params.get('db_url', 'sqlite:///TestData.db')
    db_table = params.get('db_table', 'ts_data')
    datastore = slowpy.store.create_datastore_from_url(db_url, db_table)


@webapi.post('/api/postdata')
def postdata(doc:slowlette.JSON, timestamp:float=0):
    if datastore is not None:
        datastore.append(dict(doc), timestamp=timestamp)
