---
title: Dash Start
---

<div style="font-size:120%">
If you already have:

- time-series data stored on a database, and
- `docker-compose` command available on your system,

then visualization can be done instantly (without creating a project etc.).
</div>

<img src="fig/Top-InitialPlot.png" width="50%" style="box-shadow:gray 2px 2px;margin-bottom:3em">


# PostgreSQL

### For database setup like this:
#### Database and Data Table
|  host | port | DB user | pass | database | table |
|-------|------|---------|------|---------------|------------|
|  db_host | 5432 | db_user | db_pass | my_db | my_data_table |

#### Data Schema and Contents
##### In "long format"
|       channel       |           timestamp           |  value  |
|---------------------|-------------------------------|---------|
| sccm.Inj | 2022-09-15 03:19:25.496212+00 |        0|
| V.ThrmCpl | 2022-09-15 03:19:27.612427+00 |  6.6e-05|
| mbar.IG.AS      | 2022-09-15 03:19:31.490579+00 |  2.3e-07|
| mbar.IG.MS      | 2022-09-15 03:19:31.529545+00 |    2e-09|
| mbar.IG.BS      | 2022-09-15 03:19:31.610188+00 |    4e-09|
| ...  | |

##### Or, in "wide format"
|           timestamp           | sccm.Inj |  V.ThrmCpl    | mbar.IG.AS | mbar.IG.MS | mbar.IG.BS |
|-------------------------------|------|---------|---------|---------|---------|
| 2022-09-15 03:19:25.496212+00 |    0 | 6.6e-05 | 2.3e-07 |  2e-9   | 4e-9    |
| ...  | |


### Write a docker-compose.yaml file like this:
(modify the last two lines according to your setup)

##### For "long format"
```yaml
version: '3'

services:
  slowdash:
    image: slowproj/slowdash:2406
    ports:
      - "18881:18881"
    environment:
      - "SLOWDASH_INIT_DATASOURCE_URL=postgresql://db_user:db_pass@db_host:5432/my_db"
      - "SLOWDASH_INIT_TIMESERIES_SCHEMA=my_data_table[channel]@timestamp(aware)=value"
```

##### For "wide format"
replace the last line with:
```yaml
      - "SLOWDASH_INIT_TIMESERIES_SCHEMA=my_data_table@timestamp(aware)"
```

### And run it:
```console
$ docker-compose up
```
```console
$ firefox http://localhost:18881
```


# InfluxDB
### For database setup like this:

#### Database
InfluxDB version: 2

|  host | port | organization | token | bucket | measurement |
|-------|------|---------|------|---------------|------------|
|  db_host | 8086 | my_org | my_token | my_bucket | my_meas |

#### Data Schema and Contents
- all the data in a single "measurement"
- channel name as a "tag"

(for other table structures, refer to [Data Binding section](DataBinding.html))

### Write a docker-compose.yaml file like this:
(modify the last two lines according to your setup)
```yaml
version: '3'

services:
  slowdash:
    image: slowproj/slowdash:2406
    ports:
      - "18881:18881"
    environment:
      - "SLOWDASH_INIT_DATASOURCE_URL=influxdb2://my_org:my_token@db_host:8086/my_bucket"
      - "SLOWDASH_INIT_TIMESERIES_SCHEMA=my_meas"
```

### And run it:
```console
$ docker-compose up
```
```console
$ firefox http://localhost:18881
```


# Redis Time-Series
### For database setup like this:

#### Database and Data Table
|  host | port | database |
|-------|------|---------|
|  redis_host | 6739 | 1 |

#### Data Schema and Contents
- stored in Redis Time-Series

### Write a docker-compose.yaml file like this:
(modify the last line according to your setup)
```yaml
version: '3'

services:
  slowdash:
    image: slowproj/slowdash:2406
    ports:
      - "18881:18881"
    environment:
      - SLOWDASH_INIT_DATASOURCE_URL="redis://redis_host:6739/1"
```

### And run it:
```console
$ docker-compose up
```
```console
$ firefox http://localhost:18881
```

