---
title: Dash Start
---

<div style="font-size:120%">
If you have:

- Time-series data in an existing database
- Docker Compose installed on your system

You can start visualizing your data immediately, without any additional setup.
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

##### For Long Format Data
```yaml
services:
  slowdash:
    image: slowproj/slowdash
    ports:
      - "18881:18881"
    environment:
      - "SLOWDASH_INIT_DATASOURCE_URL=postgresql://db_user:db_pass@db_host:5432/my_db"
      - "SLOWDASH_INIT_TIMESERIES_SCHEMA=my_data_table[channel]@timestamp(aware)=value"
```

##### For Wide Format Data
Use this schema configuration instead (last line):
```yaml
      - "SLOWDASH_INIT_TIMESERIES_SCHEMA=my_data_table@timestamp(aware)"
```

### And run it:
```console
$ docker compose up
```
Then open in your browser:
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

For alternative data structures, please refer to the [Data Binding section](DataBinding.html).

### Write a docker-compose.yaml file like this:
(modify the last two lines according to your setup)
```yaml
services:
  slowdash:
    image: slowproj/slowdash
    ports:
      - "18881:18881"
    environment:
      - "SLOWDASH_INIT_DATASOURCE_URL=influxdb2://my_org:my_token@db_host:8086/my_bucket"
      - "SLOWDASH_INIT_TIMESERIES_SCHEMA=my_meas"
```

### And run it:
```console
$ docker compose up
```
Then open in your browser:
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
services:
  slowdash:
    image: slowproj/slowdash
    ports:
      - "18881:18881"
    environment:
      - SLOWDASH_INIT_DATASOURCE_URL="redis://redis_host:6739/1"
```

### And run it:
```console
$ docker compose up
```
Then open in your browser:
```console
$ firefox http://localhost:18881
```

