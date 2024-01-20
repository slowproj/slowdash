---
title: Technical Notes
---

# Database Systems


## InfluxDB
### Setup
#### DB System
##### Arch, Nov 2022
```console
$ sudo pacman -S influxdb
```

##### Ubuntu 20.04, May 26 2022
[https://portal.influxdata.com/downloads/](https://portal.influxdata.com/downloads/)
```console
$ wget -qO- https://repos.influxdata.com/influxdb.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/influxdb.gpg > /dev/null
$ export DISTRIB_ID=$(lsb_release -si); export DISTRIB_CODENAME=$(lsb_release -sc)
$ echo "deb [signed-by=/etc/apt/trusted.gpg.d/influxdb.gpg] https://repos.influxdata.com/${DISTRIB_ID,,} ${DISTRIB_CODENAME} stable" | sudo tee /etc/apt/sources.list.d/influxdb.list > /dev/null
$ sudo apt-get update && sudo apt-get install influxdb2
```

```console
$ sudo systemctl enable influxdb
```

#### Python Module
```console
$ pip3 install influxdb-client
```

#### Web Interface
```
http://localhost:8086
```
- Initial Settings:
  - Create a user with an organization (initial login screen)
- Data Store Settings:
  - Create a bucket (`Load Data` -> `Buckets`)
  - Create an API token to access the bucket (`Load Data` -> `API Tokens`)

### Writing
```python
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS, WritePrecision

class DataStore_InfluxDB:
    def __init__(self, url, token, org, bucket):
        self.org = org
        self.bucket = bucket
        self.client = InfluxDBClient(url=url, token=token, org=self.org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

    def __del__(self):
        self.client.close()
        
    def write(self, measurement, record, timestamp=None):
        for key, value in record.items():
            point = Point(measurement).tag("channel", key).field("raw_value", float(value))
            if timestamp is not None:
                point.time(timestamp, WritePrecision.S)
            self.write_api.write(self.bucket, self.org, point)
```

### Reading
```python
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

token, org, backet = ...
idb = InfluxDBClient(url="http://localhost:8086", token=token, org=org)
api = idb.query_api()

query = '''
    import "influxdata/influxdb/schema"
    schema.measurementTagKeys(bucket: "Magnetometer", measurement: "LabJack")
'''
tables = api.query(query, org=org)
for table in tables:
    print([record.get_value() for record in table])
                
query = '''
    from(bucket: "Magnetometer") 
    |> range(start: -3600s)
    |> filter(fn: (r) => r._measurement == "LabJack")
    |> filter(fn: (r) => r._field == "raw_value")
    |> filter(fn: (r) => r.channel == "AI0")
'''
tables = api.query(query, org=org)
for table in tables:
    for record in table.records:
        print(record.get_time().timestamp(), record.values['channel'], record.get_value())

idb.close()
```






## Redis
### Setup
#### DB System
##### Redis-Stack, Ubuntu 20.04, Sep 2022
```console
$ curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
$ echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
$ sudo apt-get update
$ sudo apt-get install redis-stack-server
$ sudo systemctl start redis-stack-server
```

 - dump file (dump.rdb) will be located at `/var/lib/redis-stack`.
 - run `redis-cli config get dir` to see this location


#### Python Module
```console
$ sudo pip3 install redis
```

### Writing
#### Simple Key-Value
```python
import redis
r = redis.Redis('localhost', 6379, 1)
hist = '''{
  "bins": { "min": 0, "max": 100 },
  "counts": [ 3, 5, 8, 14, 11, 3, 6, 4, 4, 1 ]
}'''
r.set('hist00', hist)
```

#### Hash in Key-Value
```python
    name, record = "record0", {'key0': value0, 'key1', value1, ...}
    r.hset(name, mapping=record)
```

#### Redis-JSON
```python
hist = {
  'bins': { 'min': 0, 'max': 100 },
  'counts': [ 3, 5, 8, 14, 11, 3, 6, 4, 4, 1 ]
}
r.json().set('hist00', '$', hist)
```

#### Redis Time-Series
```python
# creating: only once
r.ts().create('ts0', retention_msecs=1000*86400)

while True:
  timestamp, value = ...
  r.ts().add('ts0', int(1000*timestamp), value)

```

### Reading
#### Ke-Value Hash
```python
import redis
host, port, db = 'localhost', 6379, 3
with redis.Redis(host=host, port=port, db=db, decode_responses=True) as r:
    for key in r.keys():
        if r.type(key) == 'hash':
            doc = r.hgetall(key)  # return Python dict
            print(doc)
```

#### Time-Series
```python
import sys, time, json
import redis

host, port, db = 'localhost', 6379, 3

ts_list = []
with redis.Redis(host=host, port=port, db=db, decode_responses=True) as r:
    for key in r.keys():
        if r.type(key) == 'TSDB-TYPE':
            ts_list.append(key)
            print(key)

to = time.time()
length = 100000

record = {}
start = to - length
for key in ts_list:
    ts = redis.ts().range(key, int(1000*start), int(1000*to))
    n = len(ts)
    if n == 0:
        continue
    
    t, x = [],[]
    for tk, xk in ts:
        t.append(int(10*(tk/1000-(to-length)))/10)
        x.append(xk)
    record[key.decode()] = {'start': start, 'length': length, 't': t, 'x': x}
        
json.dump(record, sys.stdout)
sys.stdout.write('\n')
```

#### JSON
```python
import redis

host, port, db = 'localhost', 6379, 3
redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)

obj_list = []
for key in redis.keys():
    if redis.type(key) == 'ReJSON-RL':
        obj_list.append(key)
        print(key)

for key in obj_list:
    print(key)
    obj = redis.json().get(key)
    print(obj)
```

## CouchDB

### Setup
#### DB System
```console
$ sudo apt update && sudo apt install -y curl apt-transport-https gnupg
$ curl https://couchdb.apache.org/repo/keys.asc | gpg --dearmor | sudo tee /usr/share/keyrings/couchdb-archive-keyring.gpg >/dev/null 2>&1
$ source /etc/os-release
$ echo "deb [signed-by=/usr/share/keyrings/couchdb-archive-keyring.gpg] https://apache.jfrog.io/artifactory/couchdb-deb/ ${VERSION_CODENAME} main" | sudo tee /etc/apt/sources.list.d/couchdb.list >/dev/null
```

```console
$ sudo apt update
$ sudo apt install -y couchdb
```
#### Python Module
```console
pip3 install couchdb
```

### Web Interface
```
http://localhost:5984/_utils/
```
### Writing
- Create a "Database" with the Web Interface

#### Basic
```python
couchdb_server = 'http://admin:admin@localhost:5984'
db_name = 'ripple'

import couchdb, uuid
couch = couchdb.Server(couchdb_server)
db = couch[db_name]

db.save({
    "_id": uuid.uuid4().hex,
    "channel": channel,
    "timestamp": timestamp,
    "meta": meta,
    "graph": graph
})
```
#### Attachment / Blob
```python
doc = {
    "_id": uuid.uuid4().hex
    "timestamp": time.time(),
    "name": file_name,
    "parameters": properties,
}
db.save(doc)
db.put_attachment(doc, blob_content, filename=file_name, content_type=mime_type)
```

### Reading

#### With a view
Create a view with the Web Interface:
```javascript
function (doc) {
    const record = {
        "Filament": doc.Config.FilamentInfo.SummaryState == 'ON' ? 1 : 0,
        "Multiplier": doc.Config.MultiplierInfo.MultiplierOn == 'Yes' ? 1 : 0,
    };
    emit(doc.timestamp, record);
}
```
Hereafter `view_name` is `DESIGN_DOCUMENT_NAME/INDEX_NAME`.

reading columns:
```python
def get_channels():
    channels = []
    view = self.db.view(view_name)
    rows = view[start_key:end_key].rows
    for key in rows[-1].value:
        channels.append({'name': key})
    return channels
```
reading values:
```python
def get_series(channel, start, to):
    t, x = [], []
    rows = db.view(view_name)[start:to].rows
    for row in rows:
        timestamp = row.key
        value = row.value.get(channel, None)
        if value is not None:
            t.append(timestamp)
            x.append(value)
    return t,x
```

#### Attachment / Blob
```python
        doc = db.get(ID)
        if doc is not None:
            content_type = doc.get('_attachments', {}).get(FILENAME, {}).get('content_type', None)
            att = db.get_attachment(doc, FILENAME, default=None)
            if content_type is not None and att is not None:
                output.write(att.read())
                att.close()
```
A blob time-series 
```javascript
function (doc) {
    const record = {
        "PhotoImage": {
            mime: doc._attachments[doc.name].content_type, 
            id: doc._id + '/' + doc.name, 
            meta: doc.properties
        }
    });
    emit(doc.timestamp, record);
}
```
