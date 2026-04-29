---
title: Prerequisites
---

# Before You Start
This page, written by Claude, summarizes the minimum background knowledge needed before following the SlowDash documentation, especially [Installation](Installation.html), [Quick Tour](QuickTour.html), [Project Setup](ProjectSetup.html), and [Data Binding](DataBinding.html).

This documentation assumes you can:

- run commands in a terminal
- edit text files (YAML, Python, HTML)
- understand basic Python script execution
- understand basic database table concepts

If you are new to some of these topics, the quick notes below are enough to get started.

# Terminal Basics
You should be comfortable with:

```console
$ pwd                 # show current directory
$ ls -la              # list files
$ cd PATH/TO/DIR      # move to a directory
$ mkdir MyProject     # create a directory
$ python3 script.py   # run a Python script
```

You will often need multiple terminals:

- one terminal for `slowdash --port=18881`
- one terminal for data generator / user task scripts

# Python and Virtual Environments
In native installation, SlowDash uses a project-local Python virtual environment (`venv`) prepared by `make`.

Typical flow:

```console
$ source PATH/TO/SLOWDASH/bin/slowdash-bashrc
$ slowdash-activate-venv
$ python your-script.py
```

What `venv` does:

- keeps dependencies isolated
- avoids breaking system Python
- ensures `slowpy` is available from your scripts

For SlowDash users, the key point is:

- know what `venv` is (an isolated Python environment)
- run `slowdash-activate-venv` before running scripts in a new terminal

Useful checks after activation:

```console
$ echo "$VIRTUAL_ENV"
$ which python
$ which pip
```

`$VIRTUAL_ENV` should be a non-empty path (for example, `.../venv`), and both `python` and `pip` should point to that environment.

When `venv` is active:

- shell prompt often shows `(.venv)` (depends on shell)
- `python` and `pip` point to `.venv/bin/...`
- packages installed by `pip` stay inside that environment

## If your system Python is too old
If your OS-provided Python is already End-of-Life (EOL), avoid building your workflow on it.
Use `pyenv` to install and select a supported Python version first, then run the normal SlowDash installation (`make`) so SlowDash sets up its `venv` with that Python.

Example flow:

```console
$ pyenv install 3.12.9
$ pyenv local 3.12.9
$ make
$ source PATH/TO/SLOWDASH/bin/slowdash-bashrc
$ slowdash-activate-venv
```

Enable `pyenv` automatically in new terminals (`.bashrc`):

```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
```

After editing `.bashrc`, reload it:

```console
$ source ~/.bashrc
```

Then verify:

```console
$ pyenv version
```

Recommended approach:

- `pyenv`: selects and manages Python runtime versions
- `venv`: isolates project dependencies
- use both together for long-term reproducibility and security updates

# YAML
SlowDash project configuration is written in YAML.

Minimal example:

```yaml
slowdash_project:
  name: QuickTour
  title: SlowDash Quick Tour
  data_source:
    url: sqlite:///QuickTourTestData.db
    time_series:
      schema: testdata[channel]@timestamp(unix)=value
```

Important YAML rules:

- indentation is semantic (use spaces, not tabs)
- `key: value` pairs define mappings
- nested blocks are created by deeper indentation

# RDBMS and SQL Basics
SlowDash commonly reads data from SQL databases (RDBMS), such as PostgreSQL, MySQL, and SQLite.
As a first image, think of RDBMS as storing data in multiple table-like sheets, similar to Excel.
(Strictly speaking, RDBMS also defines formal relations between tables, which is beyond this introductory image.)

Minimum concepts:

- a **table** stores data in rows and columns
- a **row** is one record (one timestamped measurement, for example)
- a **column** is one attribute (`timestamp`, `channel`, `value`, etc.)
- `PRIMARY KEY` uniquely identifies a row (often timestamp + channel in time-series tables)

Minimum SQL you should recognize:

- `SELECT ... FROM table` to read data
- `WHERE ...` to filter rows
- `ORDER BY ...` to sort rows
- `LIMIT N` to fetch only part of the result

Example:

```sql
SELECT timestamp, channel, value
FROM testdata
WHERE channel = 'ch00'
ORDER BY timestamp DESC
LIMIT 10;
```

You do not need advanced SQL to start Quick Tour, but these basics help when checking and troubleshooting data bindings.

# Data Time Representation
When data is recorded, each value has a timestamp.
This section explains how that timestamp itself is represented:

- `unix`: elapsed seconds from `1970-01-01 00:00:00 UTC` (UNIX epoch), timezone-independent
- `with time zone` (or `aware`)
- `without time zone` / `naive` (generally discouraged)
- `unspecified utc` (time string without zone, but known to be UTC)

Practical difference:

- `unix` is a numeric elapsed-time representation
- other types are date-time representations written as year/month/day/hour/minute/second strings

Use `unix` when possible for least ambiguity.

# Table Structure Description
Next, you need a way to describe the structure of your data table:
which column is time, which is channel tag, and which is value.
In SlowDash, this structure description is called a schema descriptor.

A common pattern is:

```
table[tag]@time_column(type)=value_column
```

Examples:

- `testdata[channel]@timestamp(unix)=value`
- `numeric_data[endpoint]@timestamp(with timezone)=value_raw`

Meaning:

- `table`: source table or measurement
- `[tag]`: column used as channel name
- `@time_column(type)`: timestamp source and type
- `=value_column`: value field

# Basic Network and Port Awareness
SlowDash server examples often use port `18881`.

- open browser to `http://localhost:18881`
- if using Docker, map `-p 18881:18881`
- ensure the port is not already occupied

# Docker and Docker Compose Basics
Containers are optional in SlowDash.
If you are not familiar with containers, you do not need to use Docker to get started; native installation is a valid and recommended first path.

When to skip containers (at first):

- you are learning SlowDash basics
- you use a single machine and simple setup
- you prefer fewer moving parts while troubleshooting

If you are new to containers, start with this mental model:

- a **container image** is a packaged runtime environment (application command + dependencies + runtime settings)
- a **container** is a running instance created from that image
- Docker runs one container with one command
- Docker Compose is a tool to run and coordinate multiple related containers

For SlowDash, this means:

- if Docker is already installed, you can pull an existing SlowDash image and start using SlowDash without installing SlowDash itself on your host
- you do not need to install SlowDash Python dependencies directly on your host
- your project files stay on your host machine
- the SlowDash process runs inside the container and reads your mounted project directory

Why introduce containers later:

- reproducibility: same runtime environment across machines
- cleaner host system: fewer Python packages installed globally
- easier team sharing: colleagues can run with the same image and compose file
- safer upgrades/rollbacks: switch image tags with less host-side impact
- better multi-service workflows: easy to combine SlowDash with DB/reverse-proxy/notebook services

Important options in examples:

- `-v $(pwd):/project`
  - left side (`$(pwd)`): your current host directory
  - right side (`/project`): path inside the container
  - effect: files edited on host are immediately visible in the container
- `-p 18881:18881`
  - left side: host port
  - right side: container port
  - effect: browser access to `http://localhost:18881` reaches SlowDash in the container
- `--rm`
  - remove the container automatically when it stops
  - useful for temporary test runs

Minimal single-container example:

```console
$ cd YOUR_PROJECT_DIR
$ docker run --rm -p 18881:18881 -v $(pwd):/project slowproj/slowdash
```

What happens:

1. Docker downloads the image if needed.
2. A container starts and runs SlowDash.
3. You open `http://localhost:18881` in your browser.
4. When you stop it, that container is removed (`--rm`), but your project files remain on host.

Minimal Docker Compose example:

In many practical setups, you also want a database without installing it directly on your host.
In that case, both SlowDash and the database run as containers, so you need to run at least two containers together.
Docker Compose automates this multi-container startup/shutdown from one configuration file.

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      - POSTGRES_USER=slowdash
      - POSTGRES_PASSWORD=slowdash
      - POSTGRES_DB=slowdash
    volumes:
      - postgres-data:/var/lib/postgresql/data

  slowdash:
    image: slowproj/slowdash
    depends_on:
      - postgres
    volumes:
      - .:/project
    ports:
      - "18881:18881"

volumes:
  postgres-data:
```

Why Compose is useful:

- no manual step-by-step startup of multiple containers
- one `docker compose up` can start SlowDash + database together
- one `docker compose down` can stop them together
- service definitions stay in a file and are easy to share with teammates

Start and stop:

```console
$ docker compose up
$ docker compose down
```
