---
title: Installation
---

# Docker
## Prerequisite
- `git`
- `docker` and `docker compose`

## Using Docker Images (Linux, Windows WSL, Mac)

### Setup
No installation is required. In your docker configuration, pull a SlowDash image from one of the repositories below:

- DockerHub: [slowproj/slowdash:TAG](https://hub.docker.com/r/slowproj/slowdash/tags)
- GitHub Container Registry: [ghcr.io/slowproj/slowdash:TAG](https://github.com/slowproj/slowdash/pkgs/container/slowdash)

Choose a specific tag listed in the repository, or use `latest`.

### Updating
If you are using the `:latest` images from DockerHub (or GitHub CR), removing the local copy will cause pulling the latest version on the next execution:
```console
docker rmi -f slowproj/slowdash
docker rmi -f slowproj/slowpy-notebook
```
(You can also do the same by `make docker-update` at the SlowDash directory.)

This will erase the current images. Be careful not to lose your working context. The SlowDash version number is shown in the upper left coner of the home page.



## Building an Image
### Initial Setup
```console
$ git clone https://github.com/slowproj/slowdash.git
$ cd slowdash
$ make docker
```

Or equivalently, you can run the following commands:
```console
$ git clone https://github.com/slowproj/slowdash.git --recurse-submodules
$ cd slowdash
$ docker build -t slowdash .
$ docker build -t slowpy-notebook -f ./lib/Dockerfile ./lib
```

### Updating
```console
$ cd PATH/TO/SLOWDASH
$ make update
$ make docker
```

Or equivalently, run the commands below
(be careful not to forget `--recurse-submodules`; a very common mistake, and it causes tricky troubles):
```console
$ cd PATH/TO/SLOWDASH
$ git pull --recurse-submodules
$ docker build -t slowdash .
$ docker build -t slowpy-notebook -f ./lib/Dockerfile ./lib
```


# Bare-Metal Installation
## Prerequisite
### Base System
- UNIX-like OS
  - Linux most tested
  - macOS and Windows (WSL) seem ok
<p>
- Python 3
  - Version >= 3.9
<p>
- Web Browser
  - Firefox most tested, Chrome &amp; Edge &amp; Safari ok, DuckDuckGo &amp; Opera never tested.
  - Also works on mobile devices: tested on iPad

### If not using venv
In this standard installation procedure, we use Python venv and install all the necessary packages there.

If you do not want to use venv, install the packages manually:

  -  numpy, pyyaml, psutil
  - optionally (recommanded), uvicorn (Asynchronouns Web Server module)
  - also matplotlib if SlowDash python library (SlowPy) is used
  - Python packages for the data storage system used in your setup:

|DBMS              |Python Module|
|------------------|-------------|
| PostgreSQL       | psycopg2    |
| MySQL            | mysqlclient |
| SQLite           | (none)      |
| Other SQL DBs (generic) | sqlalchemy  |
| InfluxDB         | influxdb-client  |
| Redis            | redis  |
| CouchDB            | couchdb  |
| MongoDB            | pymongo  |

See [Data Binding section](DataBinding.html) for details.


## Setup
This process will not create any files other than the git-cloned directory. Installation can be removed completely by deleting this directory.
```console
$ git clone https://github.com/slowproj/slowdash.git --recurse-submodules
$ cd slowdash
$ make
$ make setup-venv     # if you want to use venv (recommended)
```

This will create a bash file to set environmental variables. `source` it to include the settings:
```console
$ source PATH/TO/SLOWDASH/bin/slowdash-bashrc
```
For permanent installation, it might be convenient to include this line in the `.bashrc` file.

Test the installation by running the command:
```console
$ slowdash
Running in venv at /PATH/TO/SLOWDASH/venv
usage: 
  Web-Server Mode:      slowdash.py [Options] --port=PORT
  Command-line Mode:    slowdash.py [Options] COMMAND

Slowdash Version 250128 "Skykomish"

positional arguments:
  COMMAND               API query string. Ex) "config", "channels", "data/CHANNELS?length=LENGTH"

options:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  port number for web connection; command-line mode without this option
  --project-dir PROJECT_DIR
                        project directory (default: current dir if not specified by SLOWDASH_PROJECT environmental
                        variable)
...
```

Test the browser connection using an arbitrary port. As we have not yet defined a project, a warning message will be shown, but we proceed for now.
```console
$ slowdash --port=18881
23-05-15 20:12:35 WARNING: unable to find Slowdash Project Dir: specify it with the --project-dir option, set the SLOWDASH_PROJECT environmental variable, or run the slowdash commands at a project directory
listening at port 18881
```
```console
$ firefox http://localhost:18881
```
On success, the error messages below will be shown:

<img src="fig/QuickTour-Welcome.png" style="width:40%">

Type `Ctrl-c` to stop slowdash.

## Updating
```console
$ cd PATH/TO/SLOWDASH
$ make update
```

Or equivalently, run the commands below
(be careful not to forget `--recurse-submodules`; a very common mistake, and it causes tricky troubles):
```console
$ cd PATH/TO/SLOWDASH
$ git pull --recurse-submodules
$ make
```
Often `make` does not do anything, but it is safe to run it every time.


# Refreshing the browser cache: Hard Refresh
SlowDash scripts cached in user web browsers might cause troubles after the SlowDash server is updated. In that case, perform "hard refresh" the browser by clicking the `Reload` button with holding down the `Shift` key at a SlowDash page.
