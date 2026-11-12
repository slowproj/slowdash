# `kl_pg_store`

[日本語](README_ja.md)

`kl_pg_store` is a slowtask that stores the `DataPacket`s of `data.store.>` into PostgreSQL, designed for the time-series data of long-running experiments.
It uses only the basic features of PostgreSQL; the core does not depend on any extension or external tool.
The core concepts can also be applied to designs on other RDBs.
It was built to collect the slow control data of the KamLAND2 experiment, but **nothing in it is specific to KamLAND; it is a general-purpose setup**.

The assumed scale is 1000 channels, 100 rows/s (10 channels per message), kept forever (an experiment of ~30 years).
At this scale, it grows by about 3.2 billion rows, about 300 GB, per year.

This directory contains the PostgreSQL schema definition (tables, views, functions, roles), the slowtask that stores values into that database, and an example configuration for Slowdash.
There are also admin scripts and an example to run the database with docker.
The DB schema works independently of the slowtask.
Other applications can write without the slowtask, by calling SQL functions such as `insert_records()` directly.

## Contents

 - [Design principles](#design-principles)
 - [Dash start](#dash-start)
    - [1. Start the DB](#1-start-the-db)
    - [2. Configure Slowdash](#2-configure-slowdash)
    - [3. Send and view data](#3-send-and-view-data)
    - [4. Describe the channels](#4-describe-the-channels)
 - [Core concept](#core-concept)
 - [PostgreSQL database details](#postgresql-database-details)
    - [Install](#install)
    - [Data of the docker DB](#data-of-the-docker-db)
    - [The insert function](#the-insert-function)
    - [Value types](#value-types)
    - [Rejections](#rejections)
    - [Bulk loading past data](#bulk-loading-past-data)
    - [Managing channels](#managing-channels)
    - [Partitions](#partitions)
    - [Latest values](#latest-values)
    - [Roles](#roles)
    - [Settings](#settings)
    - [Direct operations](#direct-operations)
    - [Performance and indexes](#performance-and-indexes)
 - [Using from Slowdash](#using-from-slowdash)
    - [Setup](#setup)
    - [Running Slowdash in docker](#running-slowdash-in-docker)
    - [The channel page](#the-channel-page)
    - [How the slowtask works](#how-the-slowtask-works)
 - [Not adopted](#not-adopted)


## Design principles

 - A single entry point. All writes go through `insert_records()`; direct INSERTs into the tables are not allowed. Input validation, automatic channel creation, partition creation and updating the latest values all happen inside this function.
 - Read with simple SQL. Data is read with plain `SELECT` or `COPY` on views such as `records`. No complex mechanism is hidden inside, and it looks like a natural data source to Slowdash.
 - Received data is never deleted. Rejected inputs are also kept, all of them, in the `rejections` table.
 - The integration with the Slowdash mesh is tested.


## Dash start

Start the DB -> configure Slowdash -> send and view data -> describe the channels

### 1. Start the DB
```bash
cd toolbox/tasks/kl_pg_store/docker
echo 'POSTGRES_PASSWORD=<your_password>' > .env     # password of the superuser postgres
docker compose up -d
docker compose exec db psql -U postgres -d kldb -c '\password kl_writer'
docker compose exec db psql -U postgres -d kldb -c '\password kl_monitor'
```
PostgreSQL 16 starts, and on the first start the store is installed by `sql/install.sql`.
Choose the role passwords yourself and set them with `\password` (the same as the [Install](#install) without docker).

The environment variables (written in `docker/.env`) are below. Except `KL_DB_PORT` and `KL_DATA`, they are used only on the first start (when the database is created).

| Variable            | Default    | Description                                                      |
| ------------------- | ---------- | ---------------------------------------------------------------- |
| `POSTGRES_PASSWORD` | (required) | Password of the superuser `postgres`                             |
| `KL_DB_PORT`        | `15432`    | Published port. Other hosts can also connect                     |
| `KL_DB_NAME`        | `kldb`     | Database name                                                    |
| `KL_DATA`           | `kl_data`  | Where the data is kept: a docker volume name or a host directory |

The initial setup is as follows.

 - Connect to `<DB host>:15432` (`localhost:15432` from the same host), database `kldb`, schema `kl_store`.
   The port is published on all network interfaces; use it inside a closed network.
 - The roles `kl_admin`, `kl_writer`, `kl_monitor` and `kl_analyzer` are created (see [Roles](#roles)).
   A role without a password cannot connect from outside the container, only from inside (`docker compose exec db psql -U kl_admin -d kldb`). Set passwords only for the roles you use.
 - The data is kept in the docker volume `kl_data`. It survives `docker compose down` and is deleted by `docker compose down -v`. For real use, give a host directory such as `KL_DATA=/data/kldb` (see [Data of the docker DB](#data-of-the-docker-db)).
 - To change a password later, also use `\password`.
 - `max_locks_per_transaction` is 512 (the `command` in `docker-compose.yaml`; see [The lock table](#the-lock-table)).

To install into an existing PostgreSQL without docker, see [Install](#install).


### 2. Configure Slowdash
Copy the contents of `SlowdashProject_example.yaml` into the `SlowdashProject.yaml` of your project.
```yaml
slowdash_project:
  # name, title, etc. of your project

  # KL_WRITER_DB, KL_MONITOR_DB: PostgreSQL URLs, given as environment variables
  data_source:
    url: ${KL_MONITOR_DB}
    time_series:
      schema: records[name]@ts(with timezone)=value
      tags:
        sql: SELECT DISTINCT name FROM channels WHERE type IN ('double', 'integer', 'boolean')
    object_time_series:
      schema: records[name]@ts(with timezone)=value_jsonb
      tags:
        sql: SELECT DISTINCT name FROM channels WHERE type = 'json'

  task:
    - name: "@toolbox/kl_pg_store"
      auto_start: true
      parameters:
        dsn: ${KL_WRITER_DB}
        spool: ./kl_pg_store-spool.jsonl
```

 - `name`, `title` and so on are those of your project.
 - The DB to connect to (PostgreSQL URLs) is given by the environment variables `KL_WRITER_DB` and `KL_MONITOR_DB`. For the DB of step 1, they are as below. If they are not set, the Slowdash log shows `variable substitution error: KL_WRITER_DB`.
   ```bash
   export KL_WRITER_DB=postgresql://kl_writer:PASSWORD@localhost:15432/kldb
   export KL_MONITOR_DB=postgresql://kl_monitor:PASSWORD@localhost:15432/kldb
   ```
 - `data_source`: Slowdash plots read the `records` view as `kl_monitor`. Numbers are read from `value`, and objects such as histograms from `value_jsonb`.
 - `task`: the slowtask `kl_pg_store` receives the `data.store.>` messages and writes them into the DB as `kl_writer`. Messages that could not be written are kept in the `spool` file (see [How the slowtask works](#how-the-slowtask-works)).

Start Slowdash as usual. To run Slowdash in docker, connect it to the DB as described in [Running Slowdash in docker](#running-slowdash-in-docker).

### 3. Send and view data
Send a `DataPacket` to the Slowdash WebMesh, on a topic starting with `data.store.`. `t` is the time and `x` is the value.
```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{ "env.laboratory.temperature": { "t": "2026-11-10T21:45:00+09:00", "x": 24.1 } }' \
  http://localhost:18881/api/webmesh/publish/data.store._
```
Send one more value, 10 seconds later.
```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{ "env.laboratory.temperature": { "t": "2026-11-10T21:45:10+09:00", "x": 24.3 } }' \
  http://localhost:18881/api/webmesh/publish/data.store._
```
Use the current time for `t` (so that it falls in the plot range). `t` is an ISO 8601 string with the date, the time and the timezone, or a UNIX time (`date +%s`) (`ts` in [The insert function](#the-insert-function)). One POST can also carry several channels.

The channel `env.laboratory.temperature` is created automatically, with the type (`double`) inferred from the first value.

In Slowdash, click `env.laboratory.temperature` in the Channel List to show a plot.

The data can also be read with SQL directly (run in `docker/`).
```bash
docker compose exec db psql -U kl_monitor -d kldb
```
```sql
SELECT * FROM latest;
SELECT * FROM records
  WHERE name = 'env.laboratory.temperature' AND ts > now() - interval '1 hour'
  ORDER BY ts DESC LIMIT 10;
```

### 4. Describe the channels
An automatically created channel has no unit or description. A person adds them.
```sql
SELECT describe_channel('env.laboratory.temperature', 'degC', 'Laboratory room temperature');
SELECT name, type, unit, description FROM channels;
```
This also works with the privileges of `kl_monitor`.

A channel can also be created before sending data.
```sql
SELECT create_channel('env.laboratory.pressure', 'double', 'hPa', 'Laboratory room pressure');
```
Run this as `kl_writer` (or `kl_admin`) (`docker compose exec db psql -U kl_writer -d kldb`).

To describe many channels at once, use the admin script `utils/kl_admin.py` with a CSV file (see [Admin script](#admin-script)).

They can also be described from Slowdash. The slowtask `kl_pg_store` provides the HTML panel `kl_channels`, with the list of channels, input fields for the unit and the description, and a form to create a channel (see [The channel page](#the-channel-page)).

That is enough to start operating.


## Core concept

All objects are placed in a dedicated schema (default: `kl_store`).

The `channels` table defines the channels (the names of the variables that values belong to).
```
| cid | name                         | valid_from | type   | unit | description                 |
| --- | ---------------------------- | ---------- | ------ | ---- | --------------------------- |
| 1   | env.laboratory.temperature   | -infinity  | double | degC | Laboratory room temperature |
| 2   | calc.server01.cpu_usage      | -infinity  | double | %    | server01 cpu usage          |
| 3   | analysis.onlinetool.darkrate | -infinity  | double | cps  | Online average dark rate    |
| .   | ............................ | .......... | ...... | ...  | ........................... |
```
When an unknown channel arrives, it is created automatically, with the type inferred from the first value.
A person adds the unit and the description.
Channel names are free-form; here they follow the rule `<subsystem>.<source>.<quantity>`. `source` is where the value comes from (a device, a device channel, a location, etc.), and `quantity` is the physical quantity. In general, an experiment should have a consistent naming rule.

The `raw_records` table is the table that actually holds the data, in long format (one value per row).
```
| cid | ts                   | inserted_at          | value |
| --- | -------------------- | -------------------- | ----- |
| ... | .................... | .................... | ....  |
| 1   | 2026-10-10T01:10:01Z | 2026-10-10T01:10:01Z | 23.5  |
| 1   | 2026-10-10T01:10:02Z | 2026-10-10T01:10:02Z | 23.4  |
| 2   | 2026-10-10T01:10:03Z | 2026-10-10T01:10:03Z | 60.7  |
| 1   | 2026-10-10T01:10:03Z | 2026-10-10T01:10:03Z | 23.5  |
| 3   | 2026-10-10T01:10:04Z | 2026-10-10T01:10:05Z | 13943 |
| ... | .................... | .................... | ....  |
```
In fact there are five value columns, one per type: `value` (double), `value_int`, `value_text`, `value_bool` and `value_jsonb`. In each row, only the column for the type of the channel has a value.

This table grows very large, so it is split into weekly partitions.

Users do not need to care about this table or the cid mapping; they read the `records` view by name.
```sql
SELECT * FROM records
  WHERE name = 'calc.server01.cpu_usage' AND ts > now() - interval '1 day'
  ORDER BY ts DESC LIMIT 10;
```
The columns of `records` are `name`, `ts`, `value`, `unit`, `type`, `value_int`, `value_text`, `value_bool`, `value_jsonb`, `cid` and `inserted_at`.
`value` is the value of the numeric types (double, integer, boolean) as a double; text and json values are in `value_text` and `value_jsonb`.
Slowdash also reads numbers from `value` and objects such as histograms from `value_jsonb`, in this `records` view.

Always give a `ts` range when reading `records`.
Otherwise, if many future partitions happen to exist, or the channel stopped updating long ago, the whole period of the channel is read.
If you do not know the range, find the cid from `latest` first (see [Reading the views](#reading-the-views)).

All writes go through the function `insert_records()` (see [The insert function](#the-insert-function)).

The tables and views:

| Name                | Kind  | Description                                                               |
| ------------------- | ----- | ------------------------------------------------------------------------- |
| `channels`          | table | Channel definitions                                                       |
| `records`           | view  | All data, looked up by name. Slowdash reads from here                     |
| `latest`            | view  | The latest value of each name. The same columns as `records`              |
| `rejections`        | table | Rejected inputs. Never deleted                                            |
| `raw_records`       | table | The actual data, looked up by cid. Weekly partitions                      |
| `raw_latest`        | table | The latest value of each cid. Derived; rebuilt from `raw_records`         |
| `settings_overview` | view  | List of all settings (read only)                                          |
| `settings`          | table | Settings such as the schema version and the accepted time range (one row) |
| `channel_log`       | table | History of changes to the channel definitions. Never deleted              |

Objects with `raw_` are the tables that hold the data, looked up by cid; they are not usually read directly.


## PostgreSQL database details

### Install
To install into an existing PostgreSQL (16 or later) without docker, run the following as a superuser.
On Ubuntu, `sudo apt install postgresql libpq-dev`, and run as `sudo -u postgres psql ...`.
Create the database `kldb` first (`createdb kldb`). The database name is free (this document uses `kldb`).
```bash
psql -d kldb -f sql/install.sql
psql -d kldb -c '\password kl_admin'
psql -d kldb -c '\password kl_writer'
psql -d kldb -c '\password kl_monitor'
psql -d kldb -c '\password kl_analyzer'
```
Set passwords only for the roles you use.
The store is installed into the connected database.
`install.sql` is idempotent.
Set `max_locks_per_transaction` in `postgresql.conf` large enough (e.g. 512) (see [The lock table](#the-lock-table)).
Changing it requires a server restart.
The location of `postgresql.conf` depends on how PostgreSQL was installed; `psql -c 'SHOW config_file'` shows it.
The docker DB does not edit `postgresql.conf`; it passes `-c max_locks_per_transaction=512` in the `command` of `docker-compose.yaml`.

The variables given by `-v` are below, all optional (e.g. `psql -d kldb -v schema=kl_store -v role_prefix=kl -f sql/install.sql`).

| Variable                   | Default    | Description                                                                |
| -------------------------- | ---------- | -------------------------------------------------------------------------- |
| `schema`                   | `kl_store` | The schema for all objects. The work schema is `<schema>_work`             |
| `role_prefix`              | `kl`       | Role names are `<role_prefix>_admin` etc.                                  |
| `monitor_timeout`          | `30s`      | `statement_timeout` of the monitor role. Set only when the role is created |
| `monitor_connection_limit` | `20`       | Connection limit of the monitor role. Set only when the role is created    |

Slowdash is given the DB by the environment variables `KL_WRITER_DB` and `KL_MONITOR_DB` (PostgreSQL URLs).

### Data of the docker DB
Where the data of the docker DB (the PostgreSQL data directory) is kept is chosen by `KL_DATA`.

| `KL_DATA`                         | Location                      | Deleted by                                      |
| --------------------------------- | ----------------------------- | ----------------------------------------------- |
| `kl_data` (default)               | A volume managed by docker    | `docker compose down -v`, `docker volume prune` |
| `/data/kldb` etc. (absolute path) | A host directory (bind mount) | Only by deleting the directory                  |

The default is fine for trying. For real use, give a host directory. The location is explicit, which makes choosing the disk (about 300 GB per year), backups and migration easier, and the data cannot be deleted by mistake by a docker operation.
Give an empty directory. The database is created there on the first start.

### The insert function
Partition creation and consistent data are possible because direct INSERTs into the tables are not allowed, and all input goes only through `insert_records()`.
This function keeps the input data consistent with the channel definitions.
The slowtask calls this function internally.
When only the DB definitions are used, without the slowtask (or Slowdash), the SQL functions are still responsible for validating the input.

```sql
SELECT * FROM insert_records('[
  { "name": "env.laboratory.temperature", "ts": "2026-10-10T01:10:01Z", "value": 23.5 },
  { "name": "env.laboratory.humidity",    "ts": 1791594601.25,          "value": 48.1 }
]');
```

The `records` of `insert_records(records jsonb, update_latest boolean DEFAULT true)` is a JSON array of objects with `name`, `ts` and `value`.
The admin and writer roles can execute it.

 - `ts` is an ISO 8601 string with the date, the time and the timezone (`2026-10-10T01:10:01Z`, `2026-10-10 10:10:01.5+09:00`, etc.), or a UNIX time (seconds, may be fractional).
   A date only (`2026-10-10`) or a string without a timezone is rejected, not completed: completing it would make the timezone depend on the settings, or make all values of the same day `duplicate`. Seconds may be omitted.
   A UNIX time in milliseconds (`1791594601250` etc.) is rejected as `invalid_record`.
 - If `ts` is omitted (or `null`), the server time (`statement_timestamp()`) is used. Then it equals `inserted_at`, so rows with `ts = inserted_at` can be identified as having their time completed by the server.
 - It returns only the records that could not be written (`input_index`, `status`, `cid`, `detail`). If empty, everything was written.
 - With `update_latest => false`, the table of latest values (`raw_latest`) is not updated. Use it when the latest values are known not to change, such as a bulk load of past data from CSV.

One call is one transaction.
Each record is validated, and records that fail are sent to `rejections`.
For performance, no per-record exception handling (subtransaction) is used.
On an unexpected error (such as a DB failure), the whole call fails.

#### Other write functions

| Function                                                           | Purpose                                                | Roles         |
| ------------------------------------------------------------------ | ------------------------------------------------------ | ------------- |
| `insert_record(name text, ts timestamptz, value double precision)` | Write one number. A thin wrapper of `insert_records()` | admin, writer |
| `insert_record_by_cid(cid integer, ts timestamptz, value jsonb)`   | Low-level, for administration. Takes the cid directly  | admin         |

`insert_record_by_cid()` is used by administrators, for example to fill in past data.
It does not infer types or create channels, and does not check the accepted time range.
However, it rejects a `ts` outside the validity period of the cid (`valid_from`, below).
`ts` cannot be omitted.

### Value types
A channel has one of five types: `double`, `integer`, `boolean`, `text` and `json`.
The type is fixed when the channel is created and never changes. To change the type, switch to a new channel with a new cid (`replace_channel()`, below).

When the first value of an unknown channel arrives, the channel is created automatically, with the type inferred from that value.
A channel is created only if the first value can be written. A rejected value never creates a channel.

| First value (JSON)                                       | Inferred type                                      |
| -------------------------------------------------------- | -------------------------------------------------- |
| number (including integers), `true` / `false`            | `double`                                           |
| string                                                   | `text`                                             |
| object / array (histograms etc.)                         | `json`                                             |
| `null`, the strings `"NaN"`, `"Infinity"`, `"-Infinity"` | Not inferred (rejected without creating a channel) |

`integer` and `boolean` are never inferred. If needed, create them beforehand with `create_channel()`.
A `double` represents integers up to `2**53` in absolute value exactly, so `double` is enough in most cases.

Values for an existing channel are converted as long as no information is lost.

| Value \ channel type | double    | integer                  | boolean    | text                 | json |
| -------------------- | --------- | ------------------------ | ---------- | -------------------- | ---- |
| number               | ✓         | ✓ if an integer in range | ✓ if 0 / 1 | ✓ (as a string)      | ✓    |
| `true` / `false`     | ✓ (1 / 0) | ✓ (1 / 0)                | ✓          | ✓                    | ✓    |
| string               | ✗         | ✗                        | ✗          | ✓                    | ✓    |
| object / array       | ✗         | ✗                        | ✗          | ✓ (as a JSON string) | ✓    |
| `null`               | ✗         | ✗                        | ✗          | ✗                    | ✗    |

`double` rejects NaN and ±Infinity.
An integer beyond `2**53` for a `double` is rounded to the nearest double and written. JSON numbers are often sent as doubles, and an integer-looking string cannot tell whether the original was an integer. Create channels that need exact integers as `integer`.
JSON cannot represent NaN, so the slowtask sends non-finite values as strings such as `"NaN"`.

If the inference was wrong, switch the type with `replace_channel()` (below).

### Rejections
The following inputs are rejected and kept in the `rejections` table, as they were received.
Nobody reads `rejections` daily; it exists for the principle that received data is never deleted.

| `status`                 | Description                                                                                                  |
| ------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `invalid_record`         | Malformed (not an object, empty name, `ts` cannot be parsed, etc.)                                           |
| `invalid_value`          | `null`, NaN, ±Infinity                                                                                       |
| `type_mismatch`          | ✗ in the table above                                                                                         |
| `timestamp_out_of_range` | Outside the accepted time range                                                                              |
| `out_of_validity`        | `ts` is before the first `valid_from` of the name. For writes by cid, outside the validity period of the cid |
| `duplicate`              | A value for the same channel and the same `ts` already exists                                                |
| `dropped`                | Not a rejected input, but the data of a channel deleted by `drop_channel()`                                  |

For the same channel and the same `ts`, the first value is kept and later values are rejected as `duplicate`.
Sending the same data again never stores it twice.
When `merge_channel()` moves data and the target already has a value at the same `ts`, the target value is kept and the moved value goes to `rejections` as `duplicate`.

The `record` of the data that `merge_channel()` and `drop_channel()` move to `rejections` is the input form of `insert_records()` (`name`, `ts`, `value`), plus the original `cid` and `inserted_at`.
It can be passed to `insert_records()` again.

`rejections` is never deleted, so it keeps growing if a sender is misconfigured. Check it from time to time, for example:
```sql
SELECT status, record->>'name' AS name, count(*), max(received_at)
FROM rejections WHERE received_at > now() - interval '1 day'
GROUP BY 1, 2 ORDER BY 3 DESC;
```

The accepted time range is given by `max_past` and `max_future` in the `settings` table.
The default is 100 years both into the past and the future, which effectively means no limit.
To keep data from devices with a wrong clock (a clock that went back to 1970, etc.) from scattering over periods nobody looks at, make it shorter (e.g. `UPDATE settings SET max_past = '2 months', max_future = '1 day';`). Negative values are not allowed.

### Bulk loading past data
A large amount of past data (a migration from another system, etc.) is also loaded with `insert_records()`.
Putting about 1000 records in one call makes it fast.
An example script that loads a CSV (columns `name`, `ts`, `value`):

```python
import asyncio, csv, json, sys
import asyncpg

async def main(path, dsn):
    conn = await asyncpg.connect(dsn)
    with open(path, newline='') as f:
        rows = list(csv.DictReader(f))
    for i in range(0, len(rows), 1000):
        batch = [{'name': r['name'], 'ts': r['ts'], 'value': float(r['value'])} for r in rows[i:i + 1000]]
        rejected = await conn.fetch('SELECT * FROM insert_records($1::jsonb, update_latest => false)', json.dumps(batch))
        for r in rejected:
            print(i + r['input_index'], r['status'], r['detail'], file=sys.stderr)
    await conn.close()

asyncio.run(main(sys.argv[1], 'postgresql://kl_writer:PASSWORD@localhost:15432/kldb'))
```

 - Speed: about 40,000 rows/s with one connection, and about 300,000 rows/s with 8 connections in parallel (batch 1000; a DB holding 2 years, 6 billion rows; Apple M4 Max). One year of a 1-second channel (31.5 M rows) takes about 13 minutes with one connection.
 - Space: per row, about 100 B for the table and indexes, and about 170 B of WAL. If WAL is archived, or there is a standby, that space and transfer are also needed.
 - Load the rows in `ts` order. Each call then touches fewer partitions, and the BRIN index works.
 - `insert_records()` creates the partitions of old weeks. If `max_past` has been made short, set it back during the load.
 - It can run together with the normal writes (the slowtask). In the test, the response time of the normal writes did not change while 8 connections wrote at full speed.
   However, `replace_channel()` and the like, run during the load, wait for the calls of the load to finish, and all writes stop meanwhile (see [Locking](#locking) below).
 - With `update_latest => false`, the latest values are not updated, so newly created channels do not appear in `latest`. After the load, run `SELECT rebuild_latest();` as admin.
 - After the load, vacuum as admin, with no other long transaction running.
   ```sql
   VACUUM (ANALYZE) raw_records;
   ```
   Vacuum records in the visibility map that the rows are visible to all connections.
   Without it, the queries of Slowdash plots cannot be answered from the index alone and read the heap, which is more than 10 times slower (30 days of a 1-second channel: 0.57 s became 5.2 s).
   Autovacuum also does this later, but cannot if a long transaction is running at that time (a psql connection left in `BEGIN`, a large INSERT that does not go through `insert_records()`, etc.).
   Check with `xact_start` in `pg_stat_activity`.
   For 2 years (554 GB), it took about 15 minutes (`vacuumdb -j 8`).

### Managing channels

#### Periods and cids
A channel is unique by `(name, valid_from)`; several cids can share the same name, each over its own period.
The validity period of each channel is `[valid_from, next valid_from)`.
The first channel of a name has `valid_from = -infinity` (valid for all time).

A write by name goes to the channel with the latest `valid_from` among those with `valid_from <= ts`.
Only `replace_channel()` splits periods.

On reading, the views join by cid, so looking up a name returns the histories of its cids joined together.
The `unit` and `type` of each row are those of the cid of the row.
Channel periods never overlap, so a name never returns two rows with the same `ts`.

#### Functions

| Function                                                                     | Purpose                                                    | Roles                  |
| ---------------------------------------------------------------------------- | ---------------------------------------------------------- | ---------------------- |
| `create_channel(name, type, unit, description)`                              | Create a new name                                          | admin, writer          |
| `describe_channel(name or cid, unit, description)`                           | Write the unit and the description                         | admin, writer, monitor |
| `replace_channel(name, valid_from, type, unit, description, allow_rounding)` | Switch to another channel from the time `valid_from`       | admin                  |
| `rename_channel(name or cid, new_name)`                                      | Rename                                                     | admin                  |
| `merge_channel(cid, into_name, allow_rounding)`                              | Move the data of a cid to another name, and delete the cid | admin                  |
| `drop_channel(cid)`                                                          | Delete a channel. Its data moves to `rejections`           | admin                  |

 - `create_channel()`: if the name already exists with the same type, it does nothing and returns the current cid. It is meant to be called by DAQ start-up scripts every time. A different type is an error. The unit and the description of an existing channel are not changed (a WARNING is raised if different values are given).
 - `describe_channel()`: given a name, it changes the cid with the latest `valid_from`. If a switch is scheduled with `replace_channel(name, future T)`, that is the channel after the switch. Give the cid for a past period. The values are written as given (give both the unit and the description). `NULL` means not described yet, which automatically created channels have. `''` means described as empty (for a unit, a dimensionless quantity such as `ratio_ab`). Passing `NULL` makes it not described again. The channel page and the CSV of the admin script never pass `NULL`; an empty field is written as `''`. As it changes only the unit and the description, the monitor role is also allowed. It is meant to be called from the channel page (see [The channel page](#the-channel-page)) and the admin script.
 - `replace_channel()`: the operation "from the time `valid_from`, this name becomes another channel (a new cid)". `type`, `unit` and `description`, if omitted, are taken from the channel before the switch. If `valid_from` is in the past, the data of the channel before the switch with `ts >= valid_from` is moved to the new cid. If the type changes, it runs only if all data can be converted without losing information (✓ in the table of [Value types](#value-types)), and is an error if any value cannot. Changing from `integer` to `double` is an error if some value beyond `2**53` cannot be represented exactly as a double; with `allow_rounding => true`, such values are rounded and moved.
 - `rename_channel(name, new_name)`: renames all periods of the name. The whole history goes with the new name.
 - `rename_channel(cid, new_name)`: moves only one period to a new name. Under the new name, the channel is valid for all time (`valid_from = -infinity`). Under the old name, the period becomes a continuation of the previous period (if there is no previous period, writes with a `ts` in that period are rejected as `out_of_validity`).
 - `merge_channel(cid, into_name)`: moves the data of the cid to the channels of `into_name`, each row to the cid valid at its `ts`, and deletes the cid. `into_name` may be the name of the cid itself; this undoes a `replace_channel()`. The type conversion is the same as `replace_channel()`.
 - `drop_channel(cid)`: deletes a channel. Its data moves to `rejections` as `dropped`, so it is not lost.

`rename_channel()` cannot take an existing name as `new_name`. To join an existing name, use `merge_channel()`.

#### Operations by case

| #   | Case                                                           | Operation                                                                   |
| --- | -------------------------------------------------------------- | --------------------------------------------------------------------------- |
| 1   | Define the channel beforehand                                  | `create_channel()`                                                          |
| 2   | Just send data                                                 | Created automatically (type inferred from the first value)                  |
| 3   | A DAQ start-up script calls `create_channel()` every time      | Returns the existing cid if the type is the same; an error if not           |
| 4   | Write the unit and the description after automatic creation    | `describe_channel(name)`                                                    |
| 5   | Fix the unit and the description of a past period              | `describe_channel(cid)`                                                     |
| 6   | The type inference was wrong (a string came after numbers)     | `replace_channel(name, T)` + re-insert from `rejections`                    |
| 7   | Change the type for all time (created as double, want integer) | `replace_channel(name, first ts)`. All rows move; the old cid becomes empty |
| 8   | A scheduled sensor replacement                                 | `replace_channel(name, future T)`                                           |
| 9   | Noticed a past sensor replacement afterwards                   | `replace_channel(name, past T)`. Moves the rows with `ts >= T`              |
| 10  | After a replacement, data of the old sensor arrives late       | Nothing. It goes to the old cid                                             |
| 11  | Undo a replace, or T was wrong                                 | `merge_channel(new cid, same name)`. To redo, replace again                 |
| 12  | A typo in the name, a change of the naming rule                | `rename_channel(name)`. Change the senders first                            |
| 13  | Move only one period to another name (succession)              | `rename_channel(cid)`                                                       |
| 14  | A misconfigured sender created another name and wrote data     | `merge_channel(wrong cid, right name)`                                      |
| 15  | Garbage channels made by tests or bugs                         | `drop_channel(cid)`                                                         |
| 16  | A sensor removed, end of operation                             | Nothing. Record it with `describe_channel()` if needed                      |
| 17  | Reinstalled under the same name after removal                  | Nothing if it is the same thing. Same as 8 if it is different               |
| 18  | Two sensors were writing to one name at the same time          | Not handled. They cannot be separated by ts; a person analyzes it           |

 - 6: values rejected as `type_mismatch` before the switch remain in `rejections.record` exactly as received. They can be passed again, like `SELECT insert_records(jsonb_agg(record)) FROM rejections WHERE ...`.
 - 7: the emptied old cid can be deleted with `drop_channel()`.
 - 12: if a writer keeps sending with the old name after `rename_channel()`, a new channel with the old name is created automatically. Change the name in the senders first.
 - 13: to move the period of an old sensor to another name and use the same name for a new sensor, first split the period with `replace_channel(name, T)`, then move the old period away with `rename_channel(old cid, 'x.old')`. Data of the old sensor that arrives late under the old name then does not go into the channel of the new sensor; it is rejected as `out_of_validity`. If you move it away first and let the new channel be created automatically, the new channel is valid for all time, and late data of the old sensor goes into the new channel.

#### Locking
`replace_channel()`, `rename_channel()`, `merge_channel()` and `drop_channel()` wait for running writes to finish, and make new writes wait until they complete.
They change which channel data goes to, so writes in progress must not be routed by the old definitions.
Without moving data, this takes a moment; but when moving a lot of data, or when run during a long bulk load, normal writes also stop meanwhile.
`create_channel()` and `describe_channel()` do not block writes.

Operations that move past data take time in proportion to the number of rows moved.
Estimates for a 1-second channel (a DB holding 2 years, 6 billion rows; Apple M4 Max):

| Operation                               | Speed                | 30 days (2.6 M rows) | 1 year (31.5 M rows)     |
| --------------------------------------- | -------------------- | -------------------- | ------------------------ |
| `replace_channel()` (past `valid_from`) | about 50,000 rows/s  | 43 to 53 s           | about 10 min (estimated) |
| `merge_channel()`                       | about 150,000 rows/s | 17 s                 | about 4 min (estimated)  |

 - Writes arriving meanwhile wait, and are written after it finishes. Nothing was lost in the test.
 - A lot of WAL is also written (about 13 GB for 30 days with `replace_channel()`).
 - `drop_channel()` was not measured; it moves the rows to `rejections`, so it takes as long as `replace_channel()` or longer.
 - Do large moves when the DAQ can be stopped.

#### Change history
All changes to `channels` are recorded in `channel_log` by a trigger (including changes by direct SQL, not through the functions).
Each row has the role that made the change (`logged_by`, the login role), the time, the operation (`insert`, `update`, `delete`), and the rows before and after (`old`, `new`).
The functions that move data (`replace_channel()`, `merge_channel()`, `drop_channel()`) also record one more row, with the number of rows moved etc.
Rows from the same call have the same `xact_id`.
Direct changes to `raw_records` are not recorded.

#### Admin script
`utils/kl_admin.py` is a command-line script for daily administration. It does not cover all features of the SQL; use SQL for the rest.
It requires `asyncpg` (included in the Slowdash environment).

The DB is given by `--dsn` or the environment variable `KL_ADMIN_DB` (or `KL_WRITER_DB` if not set).
```bash
export KL_ADMIN_DB=postgresql://kl_admin:PASSWORD@localhost:15432/kldb
```

| Command                                                 | Description                                                                               |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `list [string] [--unfilled]`                            | Channels with the latest values. Names containing the string; without unit or description |
| `describe <name or cid> --unit U --description D`       | Write the unit and the description (`describe_channel()`)                                 |
| `create <name> [--type T] [--unit U] [--description D]` | Create a channel (`create_channel()`)                                                     |
| `export [string] [--unfilled]`                          | Write the channels as CSV (`name`, `type`, `unit`, `description`) to the standard output  |
| `import <file> [--yes] [--create]`                      | Write the units and descriptions of a CSV                                                 |
| `rejections [--since '1 day']`                          | Summary of recent rejections (counts by status and name)                                  |

To describe many channels, export them to CSV, fill it in with a spreadsheet or an editor, and import it.
```bash
python3 utils/kl_admin.py export --unfilled > channels.csv
# edit channels.csv
python3 utils/kl_admin.py import channels.csv          # only shows the changes
python3 utils/kl_admin.py import channels.csv --yes    # writes them
```

 - Without `--yes`, `import` only shows the changes and writes nothing. With `--yes`, it writes all changes in one transaction.
 - CSV values are written as given. An empty cell is `''` (for a unit, a dimensionless quantity).
 - `export` also writes not described (`NULL`) as an empty cell. `import` skips rows that are the same as exported (untouched rows), and writes any row changed in at least one place as written. If you fill in only the description of a not described row and leave the unit empty, the unit becomes `''` (each row is treated as confirmed).
 - `describe` does not change the items whose options (`--unit` etc.) are not given.
 - A name means the current channel of the name (the cid with the latest `valid_from`). For a channel of a past period, give its cid to `describe`.
 - Names in the CSV that are not in the DB are skipped. With `--create`, they are created with the `type` in the CSV (`double` if empty). The CSV can also serve as a list to define channels beforehand.
 - `create` and `import --create` need the writer or the admin role. The others also work with the monitor role (`describe_channel()` is allowed for monitor).

### Partitions
`raw_records` is partitioned by week (the boundary is Monday 00:00 UTC).
`insert_records()` creates the partitions itself.

 - The week being written: if the partition for the week of a record does not exist, it is created on the spot.
 - The next week: each call checks whether the partition for the week after the current one exists, and creates it if not. So writes at the start of a week usually do not wait for a creation.

Creation is done in two steps, `CREATE TABLE ... (LIKE raw_records)` and `ALTER TABLE ... ATTACH PARTITION`, so other reads and writes are not blocked during creation.
(`CREATE TABLE ... PARTITION OF` locks the whole parent table and stops all reads and writes.)

To create partitions ahead from a person or an external script, use `ensure_partitions(weeks)`. It creates the partitions of this week and the next `weeks` weeks (default 4, at most 10000), and returns the number created.
```sql
SELECT ensure_partitions(52);   -- one year ahead
```
An empty partition is about 64 kB. However, the more partitions there are, the slower queries without a `ts` range become (see [Reading the views](#reading-the-views)), so there is no need to create years ahead.

Concurrent attempts to create the same partition are processed one after another.
There is no default partition.
Old partitions are kept forever. To archive them in the future, they can be detached with `DETACH PARTITION`.

### Latest values
Read the latest values from the `latest` view, one row per name.

```sql
-- current values
SELECT name, ts, value, unit FROM latest WHERE name LIKE 'env.%';

-- channels that have not been updated for 10 minutes or more
SELECT name, ts FROM latest WHERE ts < now() - interval '10 minutes';
```

`value` is the value of the numeric types (double, integer, boolean) as a double, the same as `records`. Text and json values are in `value_text` and `value_jsonb`. The exact integer value is also in `value_int`.

The actual table is `raw_latest`, which holds the latest value of each cid.
`insert_records()` groups the written records by cid before updating it, so one call updates it as many times as the number of channels (not records).
It is not updated if the `ts` is older than the current latest value.

Finding the latest value from `raw_records` directly is slow for a channel that stopped updating, because the indexes are split by partition and all partitions are scanned back.
`raw_latest` avoids this.
`raw_latest` is derived data and can be rebuilt from `raw_records` with `rebuild_latest(cid)`. Without a cid, all channels are rebuilt (about 0.2 s for 10,000 channels; writes are blocked meanwhile).
The functions that move data rebuild the `raw_latest` of the affected cids automatically.

### Roles

| Role          | Purpose                             | Privileges                                                                                                    |
| ------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `kl_admin`    | Administrator. Owner of all objects | Everything                                                                                                    |
| `kl_writer`   | DAQ, slowtask                       | Execute the write functions, `create_channel()`, `describe_channel()`, `ensure_partitions()`; read everything |
| `kl_monitor`  | Monitoring such as Slowdash         | Read, and `describe_channel()`. A short `statement_timeout` and a connection limit                            |
| `kl_analyzer` | Analysis by people                  | Read, and write into the work schema                                                                          |

All four are LOGIN roles. Changing `role_prefix` changes the `kl` part.
All roles can read `rejections` and `channel_log`.
`kl_admin` has `pg_read_all_stats` and can see the queries of all sessions in the cluster.
Note that role settings are not inherited through membership: if you create another LOGIN role as a member of these roles, the timeout does not apply.

The `search_path` of `kl_analyzer` starts with the work schema, so tables created without a schema name go into the work schema.
Note that a table with the same name as a view, such as `records`, in the work schema hides the view.

### Settings
Settings are kept in the following places by kind.
The `settings_overview` view lists all settings (read only; change each in its own place).

| Kind                            | Items                                                | Location, how to change                                              |
| ------------------------------- | ---------------------------------------------------- | -------------------------------------------------------------------- |
| Fixed at install                | `schema`, `role_prefix`                              | Variables of `install.sql`                                           |
| Behavior of the store functions | `max_past`, `max_future`                             | The `settings` table (`UPDATE settings SET ...`)                     |
| Role settings                   | `statement_timeout`, connection limit, `search_path` | `ALTER ROLE ...`. Initial values from the variables of `install.sql` |
| PostgreSQL server settings      | `max_locks_per_transaction`, `max_connections` etc.  | `postgresql.conf`                                                    |
| slowtask                        | `dsn`, `spool` etc.                                  | `SlowdashProject.yaml`                                               |

All settings for the behavior of the store functions are columns of the `settings` table (one row). Each column has a type and a CHECK constraint, so invalid values cannot be stored.
`settings.schema_version` is the version of the schema; do not change it.
PostgreSQL's own settings are not copied into the table, to avoid managing them in two places; change them with PostgreSQL's own mechanisms.

### Direct operations
When the provided functions cannot do what you need, the admin operates on `channels` and `raw_records` directly with SQL.
Keep the following invariants, which the functions maintain, after the operation.

 1. Every cid in `raw_records` exists in `channels` (there is no foreign key, so the DB does not check it).
 2. The `ts` of each row is within the validity period `[valid_from, next valid_from)` of its cid.
 3. The column with a value in each row is the column for the type of the channel.
 4. `raw_latest` matches the latest row of `raw_records` for each cid.
 5. Received data is never deleted. To delete rows, move them to `rejections` first.

A template:
```sql
BEGIN;
SET LOCAL ROLE kl_admin;
SET LOCAL search_path = kl_store;
LOCK TABLE ONLY raw_records IN SHARE MODE;   -- block writes, as replace_channel() etc. do

-- UPDATE / DELETE / INSERT here

SELECT rebuild_latest(cid) FROM ...;          -- the changed cids
SELECT * FROM check_integrity();             -- make sure this is empty
COMMIT;
```

`check_integrity(ts_from, ts_to)` checks invariants 1 to 4 and returns the violations.
1 and 3 read all of `raw_records` in the range `[ts_from, ts_to)`. Without a range, it covers all time and reads the whole table, which is heavy. 2 and 4 are checked with indexes only.
Changes to `channels` are recorded in `channel_log`, but direct changes to `raw_records` are not.

### Performance and indexes
`raw_records` has two indexes.

 - A unique index on `(cid, ts)` (B-tree). For queries that give the channel. Also used to detect duplicates.
 - A BRIN index on `ts`. For queries that read all channels over a time range. Data arrives almost in `ts` order, so it works well, and its size is a few tens of kB per partition.

Per row, the heap is about 60 B and the indexes about 37 B (554 GB for 2 years, 6 billion rows).
`rejections` has a BRIN index on `received_at` (for queries on recent rejections).
There is no foreign key from `raw_records` to `channels`; the entry functions guarantee the consistency of cids. (With a foreign key, creating a partition would lock `channels`, and could deadlock with automatic channel creation.)

#### Performance figures
Measured on a DB holding 2 years (6 billion rows) at the assumed scale (1000 channels, 100 rows/s), with PostgreSQL 16 on an Apple M4 Max (128 GB memory, SSD).

 - Writes: at the assumed load, one `insert_records()` call (10 records) takes 2.5 to 4 ms. The maximum is about 16,000 rows/s (batch 10) to 44,000 rows/s (batch 1000) with one connection, and about 320,000 rows/s with 8 connections.
 - Slowdash plots (resampled to 600 points; warm cache):

   | Channels               | 30 days | 1 year | 2 years |
   | ---------------------- | ------- | ------ | ------- |
   | 1 channel, 19 s period | 0.03 s  | 0.4 s  | 0.8 s   |
   | 10 channels, 19 s      | 0.35 s  | 4 s    | 8 s     |
   | 1 channel, 1 s period  | 0.6 s   | 7 s    | 14 s    |

   With a cold cache, it takes several times longer (about 30 s for 1 year of a 1-second channel).
   All rows of the period are read and resampled, so the time is proportional to the number of rows in the period. Long periods of 1-second channels approach the `statement_timeout` of monitor (30 s).

#### Reading the views
Views are expanded into the query, so the conditions on `name` and `ts` are used directly to choose the indexes and the partitions of `raw_records`.
However, without a `ts` range, all partitions are read.
For example, getting "the latest 10 rows" without a range reads all rows of the channel over all time and then sorts them, because the view finds the cid from the name by a join.

Each query follows `SELECT * FROM`.

| Query (latest 10 rows)                                                                        | Time (200 channels, 4 weeks, 16 M rows) |
| --------------------------------------------------------------------------------------------- | --------------------------------------- |
| `records WHERE name='x' ORDER BY ts DESC LIMIT 10`                                            | 410 ms (grows with the whole period)    |
| `records WHERE name='x' AND ts > now() - interval '1 day' ORDER BY ts DESC LIMIT 10`          | 2.8 ms                                  |
| `raw_records WHERE cid = (SELECT cid FROM channels WHERE name='x') ORDER BY ts DESC LIMIT 10` | 0.11 ms                                 |

 - Usually, give a `ts` range. Queries from Slowdash always give a range.
 - If you do not know the range (a stopped channel, etc.), find the cid from `latest`.
   ```sql
   SELECT * FROM records
     WHERE cid = (SELECT cid FROM latest WHERE name = 'x')
     ORDER BY ts DESC LIMIT 10;
   ```
   The cid is determined first, so it reads from the newest partition and stops at the number of rows needed. Even for a stopped channel, it is fast regardless of the length of the period.
   The cid in `latest` is the cid with the newest row of the name. If the name has several cids (after `replace_channel()`), only the rows of that cid are returned. Periods do not overlap, so no wrong rows are returned, but right after a switch there may be fewer rows than requested.
   In that case, read each cid from the newest.
   ```sql
   SELECT r.* FROM (SELECT cid FROM channels WHERE name = 'x') c
    CROSS JOIN LATERAL (SELECT * FROM raw_records r WHERE r.cid = c.cid ORDER BY r.ts DESC LIMIT 10) r
    ORDER BY r.ts DESC LIMIT 10;
   ```
   Queries from Slowdash always give a `ts` range, so this problem does not occur there.

 - If you need only the current values, use `latest`.
 - A query without a range gets slower as the history gets longer. In the 2-year test, the latest row of a 1-second channel (63 M rows) without a range exceeded the `statement_timeout` of monitor (30 s). It reads the whole heap meanwhile, so the normal writes were also delayed by a few seconds.
 - Write the `ts` range as time values (`ts > '2026-11-01 00:00+09'`, etc.). A condition with `now()` (`ts > now() - interval '1 day'`) has no value until execution, so partitions cannot be pruned at planning, and like a query without a range, it opens and locks all partitions (about 0.25 s of planning with 30 years of partitions). Slowdash embeds the time values in its queries, so it is not affected.

The approaches considered and not adopted are in [Not adopted](#not-adopted).

#### The lock table
30 years of partitions is about 1560 partitions.
A query whose `ts` range is not known at planning (a query without a range, or a condition with `now()`) locks all partitions and their indexes: about 3 times the number of partitions per query, which is about 4700 for 30 years.
Locks are held until the end of the transaction, so a psql connection left in `BEGIN` keeps holding them.
The size of the PostgreSQL lock table is roughly `max_locks_per_transaction × max_connections`. When it runs out, queries fail with `out of shared memory`.
With the default (64 × 100 = 6400), two such queries running at the same time run out, so set `max_locks_per_transaction` large enough (e.g. 512; changing it needs a server restart).

 - With 512 and 30 years of partitions, up to 40 such queries ran at the same time. With 80, half of them failed. For 30 years of operation, use 1024 to 2048.
 - `insert_records()` fits in the per-connection lock slots (fast-path), so the normal writes did not fail even when the lock table was full. However, creating a new partition uses the shared lock table.

#### Query statistics (optional)
Not needed for the store to work, but useful for finding slow queries.
`pg_stat_statements` (an extension bundled with PostgreSQL) aggregates the executed queries by their form without constants (calls, total time, mean time, blocks read, etc.).
For example, it shows which Slowdash plot queries are heavy, and whether queries without a `ts` range are running.

To enable it, the library must be loaded when the server starts.
For the docker DB, add `-c shared_preload_libraries=pg_stat_statements` to the `command` in `docker-compose.yaml`, and recreate it (`docker compose up -d`). Otherwise, add it to `shared_preload_libraries` in `postgresql.conf` and restart the server.
Then run the following once in the database, as a superuser.
```sql
CREATE EXTENSION pg_stat_statements;
```

The queries with the largest total time:
```sql
SELECT calls, round(total_exec_time) AS total_ms, round(mean_exec_time, 1) AS mean_ms,
       r.rolname, left(query, 80) AS query
FROM pg_stat_statements s JOIN pg_roles r ON r.oid = s.userid
ORDER BY total_exec_time DESC LIMIT 20;
```
`SELECT pg_stat_statements_reset();` resets the statistics.
`kl_admin` can read the statistics of all roles (`pg_read_all_stats`). Other roles can read only the statistics of their own queries.

#### Concurrent writes
If the same data is sent at the same time from different connections in opposite orders, one of the calls may fail as a whole by a deadlock (for example, when a spool replay overlaps with another resend).
The slowtask keeps failed messages in the spool, so nothing is lost if they are replayed.


## Using from Slowdash

### Setup
An example of what to add to `SlowdashProject.yaml` is `SlowdashProject_example.yaml` (step 2 of [Dash start](#dash-start)).

 - Numeric channels are read from `value` of `records`, and json channels (histograms etc.) from `value_jsonb`.
 - Without `tags`, Slowdash scans all data to get the list of channels. Always give it.
 - `kl_monitor` has a `search_path`, so `records` can be written without the schema name.
 - `@toolbox/kl_pg_store` points to the slowtask in `toolbox/tasks/kl_pg_store/` of the Slowdash installation. When running Slowdash in docker, if the image does not include `toolbox/`, mount the `toolbox/` of this repository at `/slowdash/toolbox`. The steps are in [Running Slowdash in docker](#running-slowdash-in-docker), next.
 - The slowtask uses `asyncpg`. It is included in `requirements.txt` if `pg_config` is available when Slowdash is installed.
 - The DB is given by the environment variables `KL_WRITER_DB` and `KL_MONITOR_DB` (PostgreSQL URLs).

### Running Slowdash in docker
The DB publishes its port, so the Slowdash container connects to it like any other client, with the host name (or IP address) and the published port (default `15432`).
`localhost` in a container is the container itself, so `localhost:15432` cannot be used.

Put the following `docker-compose.yaml` in your project directory (where `SlowdashProject.yaml` is).
```yaml
services:
  slowdash:
    image: slowproj/slowdash
    ports:
      - "18881:18881"
    volumes:
      - .:/project
      - /path/to/slowdash/toolbox:/slowdash/toolbox:ro   # toolbox/ of this repository
    environment:
      - KL_WRITER_DB=postgresql://kl_writer:PASSWORD@dbhost:15432/kldb
      - KL_MONITOR_DB=postgresql://kl_monitor:PASSWORD@dbhost:15432/kldb
```
```bash
docker compose up -d
```

 - Replace `dbhost` with the host name of the DB. If the DB is on the same host, use `host.docker.internal`; on Linux, also add `extra_hosts: ["host.docker.internal:host-gateway"]`.
 - The image does not include `toolbox/`, so mount the `toolbox/` of this repository. Replace `/path/to/slowdash` with the path in your environment.
 - `KL_WRITER_DB` and `KL_MONITOR_DB` are the same as in step 2 of [Dash start](#dash-start). `PASSWORD` is the one set with `\password`.
 - The spool file (`./kl_pg_store-spool.jsonl`) is written in the mounted project directory.

To use your local Slowdash (a checkout of this repository), build an image with the `Dockerfile` at the top of the repository, and use it as the `image`.
```bash
cd /path/to/slowdash
docker build -t slowdash:local .
```
```yaml
    image: slowdash:local
```

 - The image contains `app/`, `lib/` etc. as of the build. After changing Slowdash itself, build again and recreate the container with `docker compose up -d`.
 - `toolbox/` is not in the image; the mounted one above is used. Changes to the slowtask (`toolbox/tasks/kl_pg_store/`) take effect by restarting Slowdash (`docker compose restart`), without a build.

### The channel page
The slowtask `kl_pg_store` provides the HTML panel `kl_channels`.
To show it:

 1. On the Slowdash home, create a new plot layout (`New Plot Layout`).
 2. From `Add a New Panel`, which appears when the mouse is on an empty part of the layout, choose `HTML Form`.
 3. Choose `kl_channels` as the HTML File, and turn on `reload HTML` of `On Update`. After a button is pressed, the page is reloaded and shows the result.
 4. Save the layout; it can then be opened from the list on the home.

If the slowtask is not running, `kl_channels` is not in the choices.

The page can:

 - Create a channel: calls `create_channel()`. The values of the input fields are written as given; an empty field is `''`. An existing name changes nothing and shows an error (use `Set` to change it).
 - List the channels: shows cid, name, `valid_from`, type, unit, description, the latest value (doubles with 6 significant digits), and its `ts` and `inserted_at`. The time of the latest value shows the channels that stopped updating.
 - Change the unit and the description: `Set` writes the values of the input fields of the row as given (calls `describe_channel()` with the cid). An empty field is `''` (for a unit, a dimensionless quantity). A field not described yet (`NULL`) shows `unfilled` in gray.

An HTML panel cannot use JavaScript or keep a state, so the slowtask keeps a single filter, sort and page, shared by everyone who has the page open.
If `reload HTML` is off, the page is not reloaded after a button is pressed, and nothing seems to change.
The page is implemented in `kl_channel_page.py`; the slowtask only loads it.

Note that Slowdash parses form values once as JSON, so ambiguous values change.
It is a known issue that `1.50` in a description becomes `1.5`, and `null` in a unit becomes `None`.
We hope this will be solved simply, with a mechanism supported by Slowdash in the future.

The functions run in the slowtask, on the `kl_writer` connection, so anyone who can open the Slowdash page can change and create channels.

The `parameters` of the slowtask:

| Parameter | Default                   | Description                                       |
| --------- | ------------------------- | ------------------------------------------------- |
| `dsn`     | (required)                | PostgreSQL URL to connect to as `kl_writer`       |
| `schema`  | `kl_store`                | The schema given to `install.sql`                 |
| `spool`   | `kl_pg_store-spool.jsonl` | Where messages that could not be written are kept |

### How the slowtask works
It calls `insert_records()` once per SlowMesh message.
The values of a `DataPacket` are sent as they are, as JSON values. The DB does the type inference and the conversion.
numpy values are converted before sending: scalars to Python numbers or bools, and arrays to lists (`np.float32(1.5)` to `1.5`, `np.array([1, 2])` to `[1, 2]`).
A `DataPacket` in the TimeSeries format is expanded into one record per time. The channel name is the tag itself if the field is `x`, otherwise `<tag>.<field>`.
This applies to messages in the documented form (`t` is an array). Currently, `DataPacket(TimeSeries)` of slowpy drops `t` and `start`, so it cannot be expanded per time. A field `x` is stored as one record with an array value at the receive time. A message with only other fields is treated as a message not in the form of a `DataPacket`, below.

A message not in the form of a `DataPacket` (e.g. `{"env.temp": 24.2}`; it should be `{"env.temp": {"t": ..., "x": 24.2}}`; also a dict with neither `x` nor an array `t`) is not discarded either: it is sent as a record without `value`, and kept in `rejections` in its original form as `invalid_record`.

Rejected records are (for now) written to the log of the slowtask (they are also kept in `rejections` in the DB).

If a message cannot be written (the DB is down, etc.), it is appended to the `spool` file as JSON Lines.
Values without `t` get the receive time as `ts` when written to the spool (otherwise they would be stored with the replay time).
After the DB recovers, replay them with:
```bash
python3 utils/replay_spool.py postgresql://kl_writer:PASSWORD@localhost:15432/kldb kl_pg_store-spool.jsonl
```
The slowtask can keep appending to the spool during a replay. Messages that fail to replay are put back into the spool.
The appends of the slowtask and the start of a replay (the rename of the spool) are serialized by a file lock (`flock`) on `<spool>.lock`, so messages appended during a replay are not lost. The lock works on local filesystems (including docker bind mounts). Do not put the spool on NFS.
Every write to the spool (including putting back the messages that failed to replay) is `fsync`ed before going on, so it survives a power loss.
Files left by an interrupted replay (`<spool>.replaying-*`) are processed first by the next replay.
Replaying the same data more than once only rejects them as `duplicate`; nothing is stored twice.
Each line of the spool is exactly an input of `insert_records()` (a JSON array of records), so it can be edited directly before replaying if needed. Lines the DB does not accept stay in the spool.


## Not adopted

 - Summary tables: a weekly summary table, for example, can be made with a table holding the count, minimum, maximum, mean etc. per `(cid, week)`, and a function that fills it.
   The time bin, the amount of late data and the update frequency differ from experiment to experiment, and it is easy to implement, so it is not provided here.
   What matters is to make it derived data that can be rebuilt from `raw_records`, and not to touch the write path.
   Late data and data filled in by `insert_record_by_cid()` make past weeks stale, but searching for rows with `inserted_at` after the previous run tells which `(cid, week)` to rebuild.
   Rows arrive almost in `inserted_at` order, so adding a BRIN index on `inserted_at` lets you search with a small index.
 - Unit conversion: with an idea such as making the last part of the naming rule the unit (from which the physical quantity can also be guessed), something smart could be implemented, but that is left to user wrappers.
   Here, the naming rule is up to the user (still, having some rule is strongly recommended).
   Even without the unit in the name, `records` returns the `unit` of the cid at the time of each row, so a name whose unit changed on the way can be converted row by row.
 - A view that speeds up queries with the `ts` of `latest` as an upper bound: `ts <= (latest ts)` does not change the result, but it still reads all of the older period, so it is not faster.
   A lower bound would make it faster, but a lower bound (e.g. `latest ts - 1 day`) is a guess that assumes a `LIMIT`, and a view cannot see the `LIMIT`, so it cannot be built.
 - A B-tree index on `ts`: measured, and not worth it, so not added.
 - Functions for plots, convenience triggers, stored procedures: too much complexity would rather keep users from freely adapting things to their environment, so they are not added (triggers are used only for logging).
 - Automatic CLUSTER of the data of old weeks: it should gain for a single channel over a long time range, and lose for short time ranges over many channels.
   It can be done later in any way, so it is postponed.
