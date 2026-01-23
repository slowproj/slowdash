---
title: Data Binding
---

# Simple Cases
### SQL DB
If the time-series data is stored in a table `data_table` with the contents like this ("long format"):

|       channel       |           timestamp           |    value    |
|---------------------|-------------------------------|-------------|
| sccm.Alicat.Inj.Gas | 2022-09-15 03:19:25.496212+00 |            0|
| V.ThermoCo.Diss.AS  | 2022-09-15 03:19:27.612427+00 | 6.605405e-05|
| mbar.IG.Vac.AS      | 2022-09-15 03:19:31.490579+00 |     2.26e-07|
| mbar.IG.Vac.MS      | 2022-09-15 03:19:31.529545+00 |        2e-09|
| mbar.IG.Vac.BS      | 2022-09-15 03:19:31.610188+00 |        4e-09|

Then the `data source` part of the configuration looks like:
```yaml
slowdash_project:
  data_source:
    url: postgresql://USER:PASS@localhost:5432/DBNAME
    time_series:
      schema: data_table[channel]@timestamp=value
```
Change `PostgreSQL` to `MySQL` or `SQLite` for other SQL DB systems.

### InfluxDB
If only one tag is used for the channel names and one field for data values (`MEAS,channel=CH1 value=VAL1 TIME`):
```yaml
slowdash_project:
  data_source:
    url: influxdb://ORGANIZATION@localhost:8086/BUCKET/MEASUREMENT
    token: TOKEN
```

### Redis
All the time-series entries will be taken from a database:
```yaml
slowdash_project:
  data_source:
    url: redis://localhost:6739/DB
```


# Concepts and Terminologies

## Data Model
###  Time-Series Data
- All data used by SlowDash is time-series
  - Data can be a time-series of scalars
  - Data can be a time-series of histograms, graphs, tables, or trees
<p>
- For data not explicitly bound for time-stamps, the time-series data can contain a single element with a time-stamp of "neutral" or "current".
  - The "neutral" timestamp matches with any data request time intervals. 
  - The "current" timestamp matches only if the data request includes the current time.
  - Therefore, data storage can contain data without time stamps. Examples are:
    - CSV file as a table
    - ROOT files containing histograms and graphs
    - JSON / YAML file containing parameters as a tree object
    - Instant readout values ("current")
<p>
- Even if a table contains time-stamped rows, the table itself is a data block without explicit time-stamps.
  - Examples:
    - log file (table)
    - run table
    - CSV file with time-stamps in the first column
  - The contents can be converted to a time-series. Until that, the data block is a single data object.
<p>
- [TODO] `valid_from` attribute in data source description: either a timestamp/datetime, `now` ("current"), or `creation`. The default is timestamp `0`, meaning "neutral".
- [TODO] a set of data elements with different `valid_from` should allow picking up the "newest" for a given time.
<p>
- [TODO] `aggregation` parameter in data query: either `none` (default for time-series of scalars), `last` (default for time-series of objects), or `sum` (cumulative histogram / merged graph / appended table).

###  Time Representation
- Time-stamps are one of:
  - UNIX timestamp, the number of seconds since the UNIX epoch
  - ISO date time string, with explicit time-zone
  - ISO date time string, without explicit time-zone (not recommended)
    - SlowDash configuration file can specify the time-zone of the data.
    - Even if the used time-zone is UTC, it should be specified explicitly.
    - Otherwise the time-zone of the data server is used for most cases, but not guaranteed (not recommended)
  
### Data Indexing (Channels)
- Each time-series has a unique name, "channel".
- A single data element can be uniquely identified by a pair of "channel" and "time-stamp".
- A data element can be a numerical scalar value (typical), a scalar value of boolean or string, or an object such as a histogram, graph, table, tree, or blob (image etc).
- [TODO] Using an array (vector of scalars) as a data element is under consideration. A table can always be used for an array.
<p>
- In a data table, if channel names are stored as a value of a column (case 1 below), this is called a "tag".
- In a data table, column(s) that contain(s) data values is/are called "field"(s).
<p>
- Depending on the structure of the data table, "channel" can be a "tag" (case 1), "field" (case 2), or a combination of them (case 3).
<p>
- Depending on the structure of the data table, there might exist multiple tags (case 4); the additional tag(s) is/are called "flags".


### Schema Descriptor
For a table storing time-series data, a "schema descriptor" describes which columns are for timestamps, tas(s), and field(s).

#### Examples
- `data_table[endpoint_name]@timestamp=value`
- `data_table[endpoint_name,set_or_ist]@timestamp(unix)=value_raw,value_cal`
- `data_table[endpoint_name]@datetime(with timezome)=value_raw(default),value_cal`

<p>
#### Syntax
- The first word is the table name. 
- Tag names, if exist, come next. Multiple tags are separated by `,`.
- The timestamp column name follows a prefix of `@`.
- After an `=`, field column names are listed.
<p>
- If the timestamp column is inferrable, it can be omitted.
- Timestamp may have a type specifier in `()`. Type specifier is case-insensitive.
- Empty field list implies that all the columns other than the timestamp and tags are fields.
<p>
- All spaces are skipped.
- If a column name includes a special character, the entire name must be quoted with `"`.


### Restrictions
- For security reasons, for SQL databases, SlowDash accepts for column names only alphabets, digits, and tightly selected special characters such as `_`, `-`, `.`, and `:`.
- Therefore, a channel name like `';drop table datatable` is not allowed, and will be rejected, even though proper handling is technically possible.


## Channels and Data-Store Schemata
Note that the numeric data values shown here can be of any other scalar types (string etc.) or objects (histogram etc.).

### Case 1: Tag Values for Channel

|       metric        |           timestamp           |    value    |
|---------------------|-------------------------------|-------------|
| psia.Alicat.Inj.Gas | 2022-09-15 03:19:25.419417+00 |          9.6|
| degC.Alicat.Inj.Gas | 2022-09-15 03:19:25.458695+00 |        23.42|
| sccm.Alicat.Inj.Gas | 2022-09-15 03:19:25.496212+00 |            0|
| V.ThermoCo.Diss.AS  | 2022-09-15 03:19:27.612427+00 | 6.605405e-05|
| V.PS.Diss.AS        | 2022-09-15 03:19:29.387352+00 |         0.01|
| A.PS.Diss.AS        | 2022-09-15 03:19:29.416561+00 |            0|
| mbar.IG.Vac.AS      | 2022-09-15 03:19:31.490579+00 |     2.26e-07|
| mbar.IG.Vac.MS      | 2022-09-15 03:19:31.529545+00 |        2e-09|
| mbar.IG.Vac.VSS     | 2022-09-15 03:19:31.56965+00  |      1.3e-08|
| mbar.IG.Vac.BS      | 2022-09-15 03:19:31.610188+00 |        4e-09|

- Tag: `metric`
- Field: `value`
<p>
- Channel name example: `psia.Alicat.Inj.Gas`
<p>
- Schema Descriptor examples: 
  - `table[metric]@timestamp(with timezone)=value_raw`
  - `table[endpoint]@timestamp(unix)`


### Case 2: Field Names for Channel

|RunNumber| TimeStamp| sccm.Alicat.Inj| mbar.CC10.Inj| K.ThrmCpl.Diss| mbar.IG.AS|
|---------|---------|---------|---------|---------|---------|
| 3098| 1664916014| 3| 1.18467| 340.58| 5.38333e-05|
| 3097| 1664915456| 3| 1.256| 503.275| 5.36e-05| 8e-08|
| 3096| 1664914833| 3| 1.36833| 745.743| 5.38333e-05|
| 3095| 1664913608| 3| 1.447| 1154.09| 5.44e-05|
| 3094| 1664913032| 3| 1.48933| 1501.14| 5.46667e-05|
| 3093| 1664912407| 3| 1.533| 1799.61| 5.52667e-05|
| 3092| 1664911835| 3| 1.576| 2060.59| 5.56e-05|
| 3091| 1664910949| 0.1| 0.163633| 2069.99| 3.82667e-06|
| 3090| 1664910320| 0.1| 0.163533| 1820.41| 2.72333e-06|
| 3089| 1664909732| 0.1| 0.163533| 1521.82| 2.54e-06|

- Tag: none
- Fields: everything other than `TimeStamp`
<p>
- Channel name example: `sccm.Alicat.Inj`
<p>
- Schema Descriptor examples: 
  - `RunTable@TimeStamp(unix)=sccm.Alicat.Inj,mbar.CC10.Inj,K.THrmCpl.Diss,mbar.IG.AS`
  - `RunTable@TimeStamp(unix)`


### Case 3: Tag Values and Field Names for Channel
|      metric         |           timestamp           |  value_raw   |   value_cal  |
|---------------------|-------------------------------|--------------|--------------|
| psia.Alicat.Inj.Gas | 2022-09-15 03:19:25.419417+00 |          9.6 |          9.6 |
| degC.Alicat.Inj.Gas | 2022-09-15 03:19:25.458695+00 |        23.42 |        23.42 |
| sccm.Alicat.Inj.Gas | 2022-09-15 03:19:25.496212+00 |            0 |            0 |
| V.ThermoCo.Diss.AS  | 2022-09-15 03:19:27.612427+00 | 6.605405e-05 | 6.605405e-05 |
| V.PS.Diss.AS        | 2022-09-15 03:19:29.387352+00 |         0.01 |         0.01 |
| A.PS.Diss.AS        | 2022-09-15 03:19:29.416561+00 |            0 |            0 |
| mbar.IG.Vac.AS      | 2022-09-15 03:19:31.490579+00 |     2.26e-07 |     2.26e-07 |
| mbar.IG.Vac.MS      | 2022-09-15 03:19:31.529545+00 |        2e-09 |        2e-09 |
| mbar.IG.Vac.VSS     | 2022-09-15 03:19:31.56965+00  |      1.3e-08 |      1.3e-08 |
| mbar.IG.Vac.BS      | 2022-09-15 03:19:31.610188+00 |        4e-09 |        4e-09 |

- Tag: `metric`
- Fields: `value_raw`, `value_cal`
<p>
- Channel name example: `sccm.Alicat.Inj:value_cal`
<p>
- Schema Descriptor examples: 
  - `table[metric]@timestamp(with timezone)=value_raw,value_cal`
  - `table[metric]@timestamp(with timezone)=value_raw(default),value_cal`
  - `table[metric]@timestamp(with timezone)`


### Case 4: Multiple Tags (Tag + Flag(s)) and Fields
|      metric         |  set_or_ist |           timestamp           |  value_raw   |   value_cal  |
|---------------------|-------------|-------------------------------|--------------|--------------|
| psia.Alicat.Inj.Gas |         ist | 2022-09-15 03:19:25.419417+00 |          9.6 |          9.6 |
| degC.Alicat.Inj.Gas |         ist | 2022-09-15 03:19:25.458695+00 |        23.42 |        23.42 |
| sccm.Alicat.Inj.Gas |         ist | 2022-09-15 03:19:25.496212+00 |            0 |            0 |
| V.ThermoCo.Diss.AS  |         ist | 2022-09-15 03:19:27.612427+00 | 6.605405e-05 | 6.605405e-05 |
| V.PS.Diss.AS        |         ist | 2022-09-15 03:19:29.387352+00 |         0.01 |         0.01 |
| A.PS.Diss.AS        |         ist | 2022-09-15 03:19:29.416561+00 |            0 |            0 |
| mbar.IG.Vac.AS      |         ist | 2022-09-15 03:19:31.490579+00 |     2.26e-07 |     2.26e-07 |
| mbar.IG.Vac.MS      |         ist | 2022-09-15 03:19:31.529545+00 |        2e-09 |        2e-09 |
| mbar.IG.Vac.VSS     |         ist | 2022-09-15 03:19:31.56965+00  |      1.3e-08 |      1.3e-08 |
| mbar.IG.Vac.BS      |         ist | 2022-09-15 03:19:31.610188+00 |        4e-09 |        4e-09 |

- Tag: `metric`
- Flag(s) `set_or_ist`
- Fields: `value_raw`, `value_cal`
<p>
- Channel name example: `sccm.Alicat.Inj:value_cal:ist`
<p>
- Schema Descriptor example: `table[metric,set_or_ist]@timestamp(with timezone)=value_raw,value_cal`



# RDBMS (SQL Database)

## Supported Database Systems
|DBMS              |Python Module Used|Async | Server-side <br>down sampling |
|------------------|-------------|------|--------------------|
| PostgreSQL       | psycopg2    |   no | yes |
| PostgreSQL - Async access      | asyncpg     |  yes | yes |
| MySQL            | mysql-connector-python |   no | yes |
| MySQL   - Async access         | aiomysql    |  yes | yes |
| SQLite           | (none)      |   no | no |


## Configuration

#### PostgreSQL
Write SlowDash project configuration file (`SlowdashProject.yaml`) like below.
```yaml
slowdash_project:
  data_source:
    url: postgresql://USER:PASS@HOST:PORT/DB
    schema: TABLE [ TAG_COLUMN ] @ TIME_COLUMN
```

#### MySQL
Write SlowDash project configuration file (`SlowdashProject.yaml`) like below.
```yaml
slowdash_project:
  data_source:
    url: mysql://USER:PASS@HOST:PORT/DB
    schema: TABLE [ TAG_COLUMN ] @ TIME_COLUMN
```

#### SQLite
Write SlowDash project configuration file (`SlowdashProject.yaml`) like below. The SQLite DB file path is relative to the project directory.
```yaml
slowdash_project:
  data_source:
    url: sqlite:///FILENAME
    schema: TABLE [ TAG_COLUMN ] @ TIME_COLUMN
```

### Avoiding Channel Scanning Overhead
To obtain a list of channels, SlowDash executes a query like `SELECT DISTINCT tag FROM table`, which can be slow if the table is large. This can be avoided either by manually listing the channels or by providing an efficient SQL statement:

#### By a manual list
```yaml
      time_series:
        schema: numeric_data[endpoint]@timestamp(with timezone)=value_raw
        tags:
           list: [ "Ch0", "Ch1", "Ch2", "Ch3" ]
```
#### By a SQL query
If the database has a channel table, separately from the data table:
```yaml
      time_series:
        schema: numeric_data[endpoint]@timestamp(with timezone)=value_raw
        tags:
           sql: "select name from endpoint_table"
```

### Time-stamp Considerations
SlowDash can handle several different data time-stamp types:

- UNIX timestamp (`unix`): number of seconds since the UNIX epoch, always safe
- DateTime type with time-zone (`aware` or `with time zone`): maybe useful
- DateTime type without time-zone (`naive` or `without time zone`): strongly discouraged
- DateTime type in UTC (`unspecified utc`): sometimes necessary

#### PostgreSQL
PostgreSQL supports several different time types:

- UNIX timestamp: as `INTERGER`/`BIGINT` (32/64 bit), or `REAL`/`DOUBLE PRECISION` (32/64 bit)
- DateTime with time-zone: `TIMESTAMP WITH TIME ZONE` / `TIMESTAMPTZ`
- DateTime without time-zone (DISCOURAGED): `TIMESTAMP`

`TIMESTAMP WITH TIME ZONE` is recommended for use with SlowDash.

#### MySQL
MySQL supports several different time types:

- UNIX timestamp: as `INTERGER`/`BIGINT` (32/64 bit) or `FLOAT`/`REAL`/`DOUBLE` (32/64/64 bit)
- DateTime without time-zone (DISCOURAGED): `DATETIME`
- DateTime in UTC: `TIMESTAMP`

The MySQL libraries used in SlowDash (aiomysql) cannot handle time-zone with the TIMESTAMP type, therefore if the `TIMESTAMP` type is used, it must be specified in SlowDash configuration file as `unspeficied utc`. Using the UNIX timestamps is always safe.

UNIX timestamps as `REAL` is recommended for use with SlowDash.

#### SQLite
SQLite does not have a dedicated date-time type, and time information can be stored in a time-string as TEXT or UNIX timestamps as INTEGER/REAL. If a field is declared as `DATETIME`, it uses TEXT for time string in UTC.

- UNIX timestamp: as `INTERGER` (64 bit) or `REAL` (64 bit)
- DateTime string in UTC: `DATETIME`

If the time string in TEXT (or `DATETIME`) is used, it must be specified in SlowDash configuration file as `unspeficied utc`. Using the UNIX timestamps is always safe.

UNIX timestamps as `REAL` are recommended for use with SlowDash.

## Time-Series of Scalar Values
To access a table containing time-series data, write the schema in the `time_series` entry:
```yaml
slowdash_project:
  data_source:
    url: postgresql://p8_db_user:****@localhost:5432/p8_sc_db
    time_series:
      schema: numeric_data[endpoint]@timestamp(with timezone)=value_raw
```

#### Case 1: Tag Values for Channel
```yaml
      time_series:
        schema: numeric_data[endpoint]@timestamp(with timezone)=value_raw
```

#### Case 2: Fields for Channel 
```yaml
      time_series:
        schema: numeric_data@timestamp(with timezone)=value_raw,value_cal
```

#### Case 3: Tag and Fields for Channel 
```yaml
      time_series:
        schema: numeric_data[endpoint]@timestamp(with timezone)=value_raw(default),value_cal
```

#### Case 4: Tag, Flags, and Fields for Channel 
[TODO] Flags are currently not supported. To use the case 4 schemata, use the `where` and `suffix` options.
```yaml
      time_series:
        schema: numeric_data[endpoint]@timestamp(with timezone)=value_raw(default),value_cal
        where: ist_or_set='ist'
        suffix: ':ist'
```

##  Time-Series of Histograms, Graphs, Tables & Trees
- store JSON string as data value
- use `object_time_series` entry
```yaml
slowdash_project:
  data_source:
    url: postgresql://p8_db_user:****@localhost:5432/p8_sc_db
    object_time_series:
      schema: histograms[channel]@timestamp(unix)=json
```

##  Time-Series of Blobs
[TODO] DB system specific?

## SQL Query Result as a Table
```yaml
slowdash_project:
  data_source:
    url: sqlite:///RunTable.db
    view:
      name: RunTable
      sql: select * from RunTable where TimeStamp >= ${FROM_UNIXTIME} and TimeStamp < ${TO_UNIXTIME}
```
- The channel "RunTable" will return a single table object with time-stamp of "current".
<p>

- Currently available variable substitutions are:
  - `${FROM_UNIXTIME}`, `${TO_UNIXTIME}`
  - `${FROM_DATETIME}`, `${TO_DATETIME}`
  - `${FROM_DATETIME_NAIVE}`, `${TO_DATETIME_NAIVE}`
  - `${FROM_DATETIME_UTC}`, `${TO_DATETIME_UTC}`


# InfluxDB
## Time-Series of Scalar Values
For simple cases, just specify the Measurement name in the `time_series` entry:
```yaml
slowdash_project:
  data_source:
    url: influxdb://SlowDash@localhost:8086/TestData
    token: MY_TOKEN_HERE
    time_series:
      - measurement: TestTimeSeries
```
or in a short form:
```yaml
slowdash_project:
  data_source:
    url: influxdb://SlowDash@localhost:8086/TestData/TestTimeSeries
    token: MY_TOKEN_HERE
```

### Non-minimal Configuration

#### Case 1: Tag Values for Channel (`meas,channel=CH1 value=VAL1 TIME`)
If there is only one Tag for channels and one Field for data values, the simple configuration above works. For data containing multiple tags and/or fields, specify the names using `schema`:
```yaml
      time_series:
        schema: meas[channel]=value
```

#### Case 2: Fields for Channel  (`meas ch1=VAL1,ch2=VAL2 TIME`) 
If the data does not have any Tags and all the Fields are used, the simple configuration above works. For data containing multiple tags and/or fields, specify the names using `schema`:
```yaml
      time_series:
        schema: meas=ch1,ch2
```

#### Case 3: Tag and Fields for Channel  (`meas,channel=CH1 value_raw=VALRAW,value_cal=VALCAL TIME`)
Use `schema` to describe which tag and fields are used:
```yaml
      time_series:
        schema: meas[channel]=value_raw(default),value_cal
```

### Specifying Data Period
Channel names (tag values and fields) are obtained through InfluxDB queries; however InfluxDB defaults do not extend back to a long range. The data time range for channel scan can be specified in the configuration:
```yaml
      time_series:
        schema: meas
        tags:
          scan_date: 2025-01-01
          scan_length: 100d
```
The tag values and fields are scanned for the time range `scan_date - scan_length` to `scan_date`. Default `scan_date` is `now()` and default `scan_length` is `10d`. For the scan length, the following length units are available: `s` (seconds: default), `m` (minutes), `h` (hours), `d` (days), `w` (weeks), and `y` (years).


##  Time-Series of Histograms, Graphs, Tables & Trees
- store JSON string as data value
- use `object_time_series` entry
```yaml
slowdash_project:
  data_source:
    url: influxdb://SlowDash@localhost:8086/TestData
    token: MY_TOKEN_HERE
    object_time_series:
      - measurement: TestTimeSeriesOfObjects
```

- In InfluxDB, time-series of scalars and time-series of objects cannot live together in the same "measurement". Use a dedicated measurement name for a time-series of objects.
- InfluxDB has a limitation on the length of the object stored as a string: this must be less than 64 kB (as of InfluxDB version 2.6)

## Time-Series of Blobs
- [TODO] store blob as a byte array



# Redis
## Data Binding
- RedisTS data can be accessed as a time-series data.
- Hash values in simple key-value stores can be accessed as "current" tree data.
- JSON values of objects (histograms etc.) in simple key-value stores can be accessed as "current" object data.
- RedisTS time-series and simple key-value of hash or JSON are automatically scanned by default.
<p>
- With a certain convention described below, time-series of objects can be constructed.

## Time-Series of Scalar Values
- Use RedisTS for time-series
- Redis key becomes the channel name

```yaml
slowdash_project:
  data_source:
    url: redis://localhost:6379
    time_series: { db: 1 }
```
or in a short form:
```yaml
slowdash_project:
  data_source:
    url: redis://localhost:6379/1
```

##  Time-Series of Histograms, Graphs, Tables & Trees

### Implementation
- Object data is stored as a JSON object in RedisJSON or as a JSON text
- Time-Series of objects (histograms, graphs, tables, and trees) are implemented by a combination of RedisTS and JSON store (RedisJSON or text).
- Each object makes one JSON entry, with a dedicated key.
- RedisTS holds a series of object keys.
- Keys are formatted as `{Channel}_{Index}`, unless specified in user configuration.
- Time-Series of objects are stored in a dedicated 'db'.
- To implement a ring buffer, `Index` is typically calculated by `int(TimeStamp % RetentionLength)`.

### Configuration File

```yaml
slowdash_project:
  data_source:
    url: redis://localhost:6379
    object_time_series: { db: 2 }
```
- The `db` parameter of the `object_time_series` indicates the database number for the time-series of objects. All the Redis-TS and Redis-JSON entries in this database will be interpreted in a specific way.

### Writer Utility
- For creating time-series objects as defined above, The `SlowPy` client library can be used:
- Example:
```python
import os, sys, time
import numpy as np
import slowpy as slp
    
redis = slp.DataStore_Redis(host='localhost', port=6379, db=1, retention_length=60)
histogram = slp.Histogram('test_histogram_01', 100, 0, 10)
graph = slp.Graph('test_graph_01', ['time', 'value'])

redis.flush_db()

tk, xk = 0, 0
while True:
    for i in range(10):
        histogram.fill(np.random.normal(5, 2))
        
    tk = tk + 1
    xk += np.random.normal(0.1, 1)
    graph.add_point(tk, xk)

    redis.write_object_timeseries(histogram)
    redis.write_object_timeseries(graph)

    time.sleep(1)
```

## Time-series of Blobs
- [TODO] store blob as string value (binary-safe, up to 1GB)

##  Hash as a Tree
- Hash values can be accessed as "current" tree objects, with a channel name equal to the key (optionally with a suffix).

##  "Current" Histograms, Graphs, Tables & Trees
- stored in Redis key-value store, either as a Redis-JSON object or as a JSON string.
- See [Data Model section](DataModel.html#value-types-and-json-representation) for the JSON structures.

<p>
- As the values are not assigned to time-stamps, those are treated as "time-neutral".
- All the RedisJSON key-value pairs in the `key_value` section will be automatically taken.
<p>
Example of a Python script to write a "current" histogram:
```python
import redis
r = redis.Redis('localhost', 6379, 1)
hist = {
  'bins': { 'min': 0, 'max': 100 },
  'counts': [ 3, 5, 8, 14, 11, 3, 6, 4, 4, 1 ]
}
r.json().set('hist00', '$', hist)
```

- The SlowPy utility can also be used to write the JSON objects: replace `write_object_timeseries()` with `write.object()`.


# MongoDB
##  Time-Series of Scalars
- [TODO] implement schema-based binding

##  Time-Series of Histograms, Graphs, Tables & Trees
- [TODO] store JSON objects

## Time-Series of Blobs
- [TODO] use GridFS



# CouchDB
## Schema
Create a CouchDB view with the key being the time-stamp, e.g.:
```javascript
function (doc) {
    const record = {
        "tag": doc.channel,
        "field01": doc.value01,
        "field02": doc.value02,
        ...
    }
    emit(doc.timestamp, record);
}
```
Here, the record fields can be scalars, JSON, or Blob-ID. Tags are optional. Multiple views can be created. Currently, only the UNIX timestamp is accepted for the key.

The SlowDash schema description for CouchDB is similar to that of SQL DB, except that a view is used instead of a table. As timestamps are used for the keys of the view, the time information is not necessary in the schema description.
```
VIEW_NAME [TAG] = FIELD1, FIELD2, ...
```
`VIEW_NAME` is `DESIGN_DOCUMENT_NAME/INDEX_NAME`.

If a view contains only data fields and all the data fields are mapped to channels, the schema description can be simply the view name.

Write the schema in the project configuration file:
```yaml
slowdash_project:
  data_source:
    url: couchdb://USER:PASS@localhost:5984/MyDB
    time_series: 
      schema: MyDesignDoc/MyIndex
```

Channels are scanned from the data, but old channels that do not appear in the last segment of data might not be found. In that case, explicitly list the channel names:
```yaml
      time_series: 
        schema: MyDesignDoc/MyIndex[Tag] = Field01, Field02, ...
        tags: 
          list: [ 'Tag01', 'Tag02', ... ]
```

##  Time-Series of Scalars
#### Case 1: Tag Values for Channel
```yaml
      time_series: 
        schema: MyDesigDoc/MyIndex[Tag]
```

#### Case 2: Fields for Channel
```yaml
      time_series: 
        schema: MyDesignDoc/MyIndex = Field01, Field02,...
```
#### Case 3: Tag and Fields for Channel 
```yaml
      time_series: 
        schema: MyDesigDoc/MyIndex[Tag] = Field01(default), Field02, ...
```

#### Case 4: Tag, Flags, and Fields for Channel 
Flags are currently not supported. Modify the CouchDB view definition in a way that a tag includes flags.

##  Time-Series of Histograms, Graphs, Tables & Trees
Store JSON objects as data values:
```javascript
function (doc) {
    const record = {
        "spectrum": {
            {
                "labels": [ "Frequency (Hz)", "FFT" ],
                "x": [ ... ],
                "y": [ ... ]
            }
        }
        ...
    };
    emit(doc.timestamp, record);
}
```

Then specify the schema in `object_time_series`:
```yaml
slowdash_project:
  data_source:
    url: couchdb://USER:PASS@localhost:5984/MyDB
    object_time_series: 
      schema: MyDesignDoc/MyIndex
```

## Time-Series of Blobs
- Save a blob object (image file etc) as a CouchDB attachment.
- Use the same structure as the time-series of objects, with the blob data type.
```javascript
function (doc) {
    const record = {
        "photo": {
            mime: doc._attachments[doc.name].content_type, 
            id: doc._id + '/' + doc.name, 
            meta: doc.parameters
        }
        ...
    };
    emit(doc.timestamp, record);
}
```

## View-Rows as a Table
A CouchDB view can be accessed as a table object with `view_table`:
```yaml
slowdash_project:
  data_source:
    url: couchdb://USER:PASS@localhost:5984/MyDB
    view_table: 
      name: DataTable
      schema: MyDesignDoc/MyIndex = Field01, Field02, ..
```

## View-Row as a Tree
A row of a CouchDB view can be accessed as a tree object with `view_tree`:
```yaml
slowdash_project:
  data_source:
    url: couchdb://USER:PASS@localhost:5984/MyDB
    view_tree: 
      name: DataRecord
      schema: MyDesignDoc/MyIndex = Field01, Field02, ..
```

## Database information as a Tree
Current database information, such as the file size, can be obtained as a tree data object. Just make a `database_info` entry in the `data_source` definition with a name:
```yaml
slowdash_project:
  data_source:
    url: couchdb://USER:PASS@localhost:5984/MyDB
    database_info: 
      name: DBInfo
```


# Local CSV Files
- A directory containing CSV files can be used as a data store, in a very similar way to tables in the RDBMS (no SQL queries, though).
- One CSV file corresponds to one table; each CSV file must have a header line for its first line.

## Time-Series of Scalar Values
To access a table containing time-series data, write the schema in the `time_series` entry:
```yaml
slowdash_project:
  data_source:
    url: csv:///PATH/TO/DIRECTORY
    time_series:
      schema: FILE_ROOT_NAME [ TAG_COLUMN ] @ TIME_COLUMN
```

##  Time-Series of Histograms, Graphs, Tables & Trees
- same as SQL databases
  - store JSON string as data value
  - use `object_time_series` entry
```yaml
slowdash_project:
  data_source:
    url: csv:///PATH/TO/DIRECTORY
    object_time_series:
      schema: histograms[channel]@timestamp(unix)=value
```

##  "Current" Histograms, Graphs, Tables & Trees
- a table without a time-stamp column stores "current" objects
- use `object` entry
```yaml
slowdash_project:
  data_source:
    url: csv:///PATH/TO/DIRECTORY
    object_time_series:
      schema: histograms[channel]=value
```


# Local YAML Files
- One YAML file stores one Tree object
- [TODO] Multiple YAML files with time-stamps encoded in the file names
- [TODO] implement `valid_from`.
```yaml
slowdash_project:
  data_source:
    type: YAML
    name: RunConfig
    file: RunConfig.yaml
    valid_from: now
```
  

# Local ROOT Files
[TODO]
