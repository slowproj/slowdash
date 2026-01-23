
'''Posting data records via HTTP-POST
- command-line example:
  - curl -X POST 'http://localhost:18881/api/postdata' --data '{"ch0":123}'
  - curl -X POST 'http://localhost:18881/api/postdata?timestamp=TIMESTAMP' --data '{"ch0":123}'
- TIMESTAMP is UNIX timestamp, 0 for "now" (default), negative N for "past N seconds"
- data is a JSON string for { channel: value, ... }
'''

db, table = 'postgresql://slowdash:slowdash@localhost:5432/SlowTestData', 'ts_data'
#db, table = 'postgresql://slowdash:slowdash@pgsql_db:5432/SlowTestData', 'ts_data'


import slowlette
webapi = slowlette.Slowlette()

import slowpy
datastore = slowpy.store.create_datastore_from_url(db, table)

@webapi.post('/api/postdata')
def postdata(doc:slowlette.JSON, timestamp:float=0):
    datastore.append(dict(doc), timestamp=timestamp)
