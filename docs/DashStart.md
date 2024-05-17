---
title: Dash Start
---

<strong>Status: Not yet available</strong> (TODO: upload a Docker image to dockerhub and ghcr)

<div style="font-size:120%">
If you already have:

- time-series data stored on a database, and
- `docker-compose` command available on your system,

then visualization can be done instantly (without creating a project etc.).
</div>

<img src="fig/Top-InitialPlot.png" width="50%" style="box-shadow:gray 2px 2px;margin-bottom:3em">


# PostgreSQL

### For database setup like this:
##### Database and Data Table
|  host | port | DB user | pass | database | table |
|-------|------|---------|------|---------------|------------|
|  db_host | 5432 | db_user | db_pass | my_db | data_table |

##### Data Schema and Contents ("long format")
|      endpoint       |           timestamp           |  value_raw  |
|---------------------|-------------------------------|-------------|
| sccm.Alicat.Inj.Gas | 2022-09-15 03:19:25.496212+00 |            0|
| V.ThermoCo.Diss.AS  | 2022-09-15 03:19:27.612427+00 | 6.605405e-05|
| mbar.IG.Vac.AS      | 2022-09-15 03:19:31.490579+00 |     2.26e-07|
| mbar.IG.Vac.MS      | 2022-09-15 03:19:31.529545+00 |        2e-09|
| mbar.IG.Vac.BS      | 2022-09-15 03:19:31.610188+00 |        4e-09|
(for the other table structure (e.g., "wide format"), refer to [Data Binding section](DataBinding.html))



### Do this for SlowDash:

write `docker-compose.yaml` as below:
```yaml
version: '3'

services:
  slowdash:
    image: slowproj/slowdash:2405
    ports:
      - "18881:18881"
    environment:
      - "SLOWDASH_INIT_DATASOURCE_URL=postgresql://db_user:db_pass@db_host:5432/my_db"
      - "SLOWDASH_INIT_TIMESERIES_SCHEMA=data_table[endpoint]@timestamp(aware)=value_raw"
```

then run:
```console
$ docker-compose up
```

and open `http://localhost:18881` with a web-browser.


# InfluxDB
### For database setup like this:

##### Database
|  host | port | organization | token | bucket | measurement |
|-------|------|---------|------|---------------|------------|
|  db_host | 8086 | my_org | my_token | my_bucket | my_meas |

##### Data Schema and Contents
- all the data in a single "measurment"
- channel name as a "tag"

(for the other table structure, refer to [Data Binding section](DataBinding.html))

### Do this for SlowDash:

write `docker-compose.yaml` as below:
```yaml
version: '3'

services:
  slowdash:
    image: slowproj/slowdash:2405
    ports:
      - "18881:18881"
    environment:
      - "SLOWDASH_INIT_DATASOURCE_URL=influxdb2://my_org:my_token@db_host:8086/my_bucket"
      - "SLOWDASH_INIT_TIMESERIES_SCHEMA=my_meas"
```
then run:
```console
$ docker-compose up
```

and open `http://localhost:18881` with a web-browser.



# Redis Time-Series
### For database setup like this:

##### Database and Data Table
|  host | port | database |
|-------|------|---------|
|  redis_host | 6739 | 1 |

##### Data Schema and Contents
- stored in Reids Time-Series

### Do this for SlowDash:

write `docker-compose.yaml` as below:
```yaml
version: '3'

services:
  slowdash:
    image: slowproj/slowdash:2405
    ports:
      - "18881:18881"
    environment:
      - SLOWDASH_INIT_DATASOURCE_URL="redis://redis_host:6739/1"
```
then run:
```console
$ docker-compose up
```

and open `http://localhost:18881` with a web-browser.

