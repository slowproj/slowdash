---
title: Related Tools Cheat Sheet
---

# About This Page
This page summarizes the key points and frequently used commands of tools that are often needed alongside SlowDash: YAML, pyenv / venv, networking, background execution and auto-start, relational databases, and Docker / Docker Compose / Docker Swarm. It is not an introduction to each tool; it is meant as a reference for when you have used a tool before but forgot the details. See the official documentation of each tool for more. This document was written by Claude.


# YAML
The SlowDash project configuration file (`SlowdashProject.yaml`) and `docker-compose.yaml` are written in YAML.

## Syntax

```yaml
# Comment (from the beginning of a line, or after a space)
name: QuickTour              # key: value (a space is required after the colon)
title: "SlowDash: Test"      # quote values containing ": " or " #"

data_source:                 # nesting by indentation (spaces only, no tabs)
  url: sqlite:///SlowStore.db

ports:                       # list
  - "18881:18881"
  - "5432:5432"

channels:                    # list of maps
  - name: ch00
    unit: K
  - name: ch01
    unit: mbar

tags: [a, b, c]              # inline list
opts: {width: 10, height: 5} # inline map

script: |                    # multi-line string (newlines kept)
  line 1
  line 2
command: >                   # multi-line string (newlines replaced with spaces)
  bash -c "echo hello"
```

## Common Pitfalls
- The indentation width can be anything, but it must be consistent within the same level. Tab characters cause an error.
- Value types are inferred automatically. Quote values that should be treated as strings:
  - `yes`, `no`, `on`, `off`, `true`, `false` become booleans (with Python's PyYAML)
  - numbers starting with 0, such as `0644`, might be interpreted as octal
  - colon-separated numbers such as `22:22` might be interpreted as base-60 numbers (always quoting port mappings, like `"22:22"`, is safe)
  - an empty value (just `key:`) becomes `null`
- Writing the same key twice is not an error; usually the later value silently overwrites the earlier one.

## Checking
To see whether the file is read as intended, convert it to JSON and print it (requires `pyyaml`, which is included in the SlowDash venv):

```console
$ python -c 'import sys,yaml,json; print(json.dumps(yaml.safe_load(open(sys.argv[1])), indent=2))' SlowdashProject.yaml
```

For `docker-compose.yaml`, `docker compose config` shows the final configuration after variable expansion.


# Python Environment: pyenv and venv

| | Manages | When to use |
|---|---|---|
| pyenv | Versions of Python itself (the interpreter) | When the OS Python is too old (EOL), or a specific version is needed |
| venv | Where packages (things you `pip install`) are installed | To isolate dependencies per project (standard in SlowDash) |

The two are independent and can be combined. A typical combination is to create a venv with a Python selected by pyenv.

## venv

```console
$ python3 -m venv venv              # create venv/ in the current directory
$ source venv/bin/activate          # activate (per shell; needed every time you open a terminal)
(venv) $ pip install numpy          # installed only into this venv
(venv) $ pip list                   # list installed packages
(venv) $ pip install -r requirements.txt
(venv) $ deactivate                 # deactivate
```

To check whether a venv is active:

```console
$ echo $VIRTUAL_ENV                 # active if the venv path is printed
$ which python                      # active if it points to .../venv/bin/python
```

Key points:

- To remove a venv, just delete the directory (`rm -rf venv`).
- Without activation, running `venv/bin/python script.py` directly uses that venv (useful when running from cron or systemd).
- A venv keeps links to the Python it was created with. It breaks if that Python is removed or updated, or if the venv directory is moved; in that case, recreate it.
- On Debian / Ubuntu, `python3-venv` might be a separate package (`sudo apt install python3-venv`).

Relation to SlowDash: `make` in the native installation creates `venv/` in the SlowDash directory. `slowdash-activate-venv` is an alias for `source $SLOWDASH_DIR/venv/bin/activate`.

## pyenv
Installation (Linux / WSL):

```console
$ curl -fsSL https://pyenv.run | bash
```

(On macOS, `brew install pyenv`.)

Then add the following to `~/.bashrc`, and either `source ~/.bashrc` or open a new terminal.

```bash
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
```

pyenv builds Python from source, so install the libraries required for the build beforehand (for Ubuntu; for other OSes, see the [pyenv Wiki](https://github.com/pyenv/pyenv/wiki#suggested-build-environment)).

```console
$ sudo apt install build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
    libsqlite3-dev libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
```

If some are missing, the build might still succeed but produce a Python without the `ssl` or `sqlite3` modules (warnings are shown during the build).

Frequently used commands:

```console
$ pyenv install --list | grep '^ *3\.'   # list installable versions
$ pyenv install 3.12.9                   # install
$ pyenv versions                         # list installed versions
$ pyenv version                          # currently active version and where it is set
$ pyenv global 3.12.9                    # set the user default
$ pyenv local 3.12.9                     # set only for this directory and below (creates a .python-version file)
$ pyenv uninstall 3.12.9
```

## Combination: Creating a venv with a pyenv Python

```console
$ cd PATH/TO/SLOWDASH
$ pyenv local 3.12.9          # python3 becomes 3.12.9 in this directory
$ rm -rf venv                 # remove the venv made with an old Python, if any
$ make                        # the venv is created with 3.12.9
```

Once the venv is created, its Python is used regardless of the pyenv settings. However, the venv breaks if the pyenv version it was created from is removed with `pyenv uninstall`.


# Network
SlowDash is used from a web browser over HTTP (the standard port is 18881). SlowDash itself has almost no security features, so it is meant to be used inside a firewall, with external access through VPN, an SSH tunnel, or a reverse proxy.

## Commands for Investigation

| Command | Purpose |
|---|---|
| `ip -br addr` | List of your IP addresses |
| `ip route` | Routing table (`default via ...` is the default gateway) |
| `ip route get ADDRESS` | Which interface and gateway are used to reach the destination |
| `ping -c 5 HOST` | Reachability and round-trip time (RTT) |
| `tracepath HOST`, `traceroute HOST` | Routers on the path and the latency to each hop |
| `mtr HOST` | Continuous display of latency and packet loss for each hop |
| `getent hosts NAME`, `dig NAME` | Name resolution (`getent` shows what programs actually get, including `/etc/hosts`) |
| `sudo ss -tlnp` | Listening TCP ports and their processes |
| `ss -tn` | Established TCP connections |
| `nc -zv HOST PORT` | Whether a TCP connection to the port can be made |
| `curl -v http://HOST:18881/` | Verbose view of an HTTP connection |
| `iperf3 -s` (on the other side), `iperf3 -c HOST` | Bandwidth measurement between two machines |
| `sudo tcpdump -i any port 18881` | Observing the actual packets |

Missing commands can be installed with `sudo apt install iputils-ping iputils-tracepath traceroute mtr-tiny dnsutils netcat-openbsd iperf3 tcpdump`.

The breakdown of HTTP response time (connection, first byte, total) can be measured with `curl`:

```console
$ curl -o /dev/null -s -w 'connect: %{time_connect}  first byte: %{time_starttransfer}  total: %{time_total}\n' http://HOST:18881/
```

Key points:

- No response to `ping` does not necessarily mean the host is unreachable (ICMP is often blocked by firewalls). Use `nc -zv` to check whether a specific port can be reached.
- If the listening address is `0.0.0.0` (or `*`), connections are accepted from all networks; if it is `127.0.0.1`, only from the same machine. Check with `sudo ss -tlnp`.
- When the display from a remote site is slow, round-trip latency (RTT) is often more important than bandwidth. If the `ping` RTT exceeds several tens of ms, switching to HTTP/2 with a reverse proxy, or placing a database mirror and SlowDash at the remote site ([Replication](#data-replication-postgresql-mysql)), might help.

## Finding Devices on the LAN
How to find the IP address of a device that gets its address by DHCP (instruments, Raspberry Pi, etc.):

```console
$ sudo arp-scan -l                          # scan the whole connected LAN; shows IP address, MAC address, and vendor
$ sudo arp-scan -I eth0 192.168.1.0/24      # specify the interface and range
$ sudo nmap -sn 192.168.1.0/24              # list responding devices (with root, MAC addresses and vendors are also shown)
$ ip neigh                                  # IP and MAC addresses of hosts this machine recently talked to (ARP cache)
```

(Install with `sudo apt install arp-scan nmap`.)

- The vendor is determined from the first part of the MAC address. Matching it with the MAC address printed on the device or its box, or comparing the list before and after powering on the device, makes it easy to find.
- ARP does not cross routers, so only devices on the same network (subnet) can be found. From inside WSL2 (in the default NAT mode) or a Docker container, the external LAN is not visible (for WSL2, use `arp -a` on the Windows side).
- On institutional networks, scanning without permission might be prohibited. Except for experiment networks you manage yourself, check with the network administrator.

## SSH Tunnel
Connect to SlowDash inside a firewall through SSH:

```console
$ ssh -N -L 18881:localhost:18881 USER@SERVER                 # local localhost:18881 -> localhost:18881 on SERVER
$ ssh -N -J USER@GATEWAY -L 18881:localhost:18881 USER@SERVER  # through a gateway (jump host)
```

Then open `http://localhost:18881` in the browser. `-N` makes a tunnel only, without running a command. To expose a port in the opposite direction, from an inside machine to an outside machine, use `-R` (see the example in [Replication](#data-replication-postgresql-mysql)).

Frequently used settings can be written in `~/.ssh/config`, so that just `ssh slowdash` connects:

```
Host slowdash
    HostName SERVER
    User USER
    ProxyJump USER@GATEWAY
    LocalForward 18881 localhost:18881
```

## Firewall (ufw)
On Ubuntu, `ufw` is used to configure the firewall (on RHEL-based systems, `firewall-cmd`).

```console
$ sudo ufw status verbose                    # current status and rules
$ sudo ufw default deny incoming             # deny incoming connections by default
$ sudo ufw default allow outgoing            # allow outgoing connections by default
$ sudo ufw allow OpenSSH                     # allow SSH (always do this before enabling!)
$ sudo ufw enable                            # enable

$ sudo ufw allow from 192.168.1.0/24 to any port 18881 proto tcp   # allow only from a specific network
$ sudo ufw allow from 203.0.113.5 to any port 5432 proto tcp       # allow only from a specific host (e.g., a DB mirror)
$ sudo ufw allow 443/tcp                     # allow HTTPS from anywhere (reverse proxy)

$ sudo ufw status numbered                   # show rules with numbers
$ sudo ufw delete 3                          # delete a rule by number
$ sudo ufw insert 1 deny from 198.51.100.7   # insert a rule at the top
$ sudo ufw reload
$ sudo ufw disable
```

Key points:

- If you are working remotely over SSH, running `ufw enable` before allowing SSH locks you out.
- Rules are evaluated from the top, and the first match is applied.
- Allow the SlowDash port (18881) only to the necessary range, such as the lab network. With a reverse proxy, do not open 18881 to the outside; open only 443 (and 80 for redirecting to HTTPS). Allow database ports (PostgreSQL 5432, MySQL 3306) only to the hosts that need to connect.
- Denied connections are logged in `/var/log/ufw.log` (`sudo ufw logging on`).
- After configuration, check from another machine with `nc -zv HOST PORT` that only the intended ports are open.

### Docker and ufw
Ports published by Docker (`docker run -p` or `ports:` in Compose) bypass the ufw rules and are reachable from outside. This is because Docker directly adds firewall rules that are evaluated before ufw.

- If access only from the same machine is needed, publish with `127.0.0.1`: `-p 127.0.0.1:18881:18881` (in Compose, `"127.0.0.1:18881:18881"`).
- If the reverse proxy runs in the same Compose setup, SlowDash does not need `ports:` (it can be reached by the service name). Publish only the reverse proxy ports.

## Reverse Proxy and HTTPS
SlowDash communicates over unencrypted HTTP/1.1. To allow external access, put a web server such as Nginx or Apache in front of it and switch to HTTPS there (reverse proxy).

```
Browser ── HTTPS (443) ──▶ Reverse proxy ── HTTP (18881) ──▶ SlowDash
                           (Nginx / Apache)                  (no direct access from outside)
```

This provides:

- Encrypted communication (HTTPS)
- Faster communication with HTTP/2 (especially effective for remote access)
- URLs without a port number (`https://HOST/slowdash/`)
- Basic authentication (HTTPS is required to protect the password)

HTTPS requires a server certificate. Use a certificate from your institution, Let's Encrypt (`certbot`; requires a host name reachable from outside), or a self-signed certificate for testing (the browser shows a warning).

For configuration, see ["Using a Reverse Proxy Server" in Project Setup](ProjectSetup.html#using-a-reverse-proxy-server); for working examples with Docker Compose, see `ExampleProjects/ReverseProxy`.


# Background Execution and Auto-Start
Server processes such as `slowdash` must keep running after the terminal is closed or the user logs out, and in production they should start automatically when the machine boots.

| Method | Survives logout | Starts at boot | Restart on failure | Logs | Suitable for |
|---|---|---|---|---|---|
| tmux / screen | yes | no | no | on screen | development, testing, temporary operation |
| nohup | yes | no | no | file | temporary operation |
| cron `@reboot` | yes | yes | no | file | simple auto-start |
| `/etc/rc.local` | yes | yes | no | file | legacy method (systemd is now recommended) |
| systemd | yes | yes | yes | `journalctl` | production in native environments |
| Docker | yes | yes | yes | `docker logs` | production in Docker environments |

In the examples below, the `slowdash` command is given by its absolute path. `bin/slowdash` activates the SlowDash venv by itself, so the venv does not need to be activated beforehand.

## tmux / screen
The whole terminal screen is kept in the background and can be reattached later. The output can be seen as is, which is convenient during development and testing.

| Operation | tmux | screen |
|---|---|---|
| Start with a name | `tmux new -s slowdash` | `screen -S slowdash` |
| Detach (the process keeps running) | `Ctrl-b` → `d` | `Ctrl-a` → `d` |
| List | `tmux ls` | `screen -ls` |
| Reattach | `tmux attach -t slowdash` | `screen -r slowdash` |
| Start detached | `tmux new -d -s slowdash 'COMMAND'` | `screen -dmS slowdash COMMAND` |
| Terminate | `tmux kill-session -t slowdash` | `screen -S slowdash -X quit` |

## nohup
Runs a process in the background so that it does not terminate on logout:

```console
$ nohup /PATH/TO/SLOWDASH/bin/slowdash --port=18881 --project-dir=/PATH/TO/PROJECT > slowdash.log 2>&1 &
$ pgrep -af slowdash      # check whether it is running (the process ID is shown)
$ kill PID                # stop
```

## cron @reboot
Adding the following line to your crontab with `crontab -e` runs it when the machine boots. No root privilege is required.

```
@reboot /PATH/TO/SLOWDASH/bin/slowdash --port=18881 --project-dir=/PATH/TO/PROJECT >> /PATH/TO/slowdash.log 2>&1
```

In the cron environment, `PATH` and others differ from a login shell, so specify commands and files with absolute paths.

## /etc/rc.local
A script executed with root privilege at boot. This is a legacy method; the file does not exist on Ubuntu by default, but if created, it is executed through systemd.

```bash
#!/bin/sh
su - USER -c '/PATH/TO/SLOWDASH/bin/slowdash --port=18881 --project-dir=/PATH/TO/PROJECT >> /PATH/TO/slowdash.log 2>&1 &'
exit 0
```

- The file must be executable (`sudo chmod +x /etc/rc.local`).
- Since it runs as root, use `su - USER -c` to run as a normal user. Put `&` at the end of processes that do not terminate, to run them in the background.

## systemd
The current standard method on Linux. systemd also takes care of restarting on failure and of logging. Create a file `/etc/systemd/system/slowdash.service` with the following contents:

```ini
[Unit]
Description=SlowDash
After=network-online.target
Wants=network-online.target
# If a database on the same machine is used, start after it:
# After=network-online.target postgresql.service

[Service]
Type=simple
User=USER
WorkingDirectory=/PATH/TO/PROJECT
ExecStart=/PATH/TO/SLOWDASH/bin/slowdash --port=18881
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```console
$ sudo systemctl daemon-reload              # run after creating or modifying a service file
$ sudo systemctl enable --now slowdash      # enable auto-start and start now
$ systemctl status slowdash                 # status and recent logs
$ journalctl -u slowdash -f                 # show logs (-f to follow)
$ sudo systemctl restart slowdash           # restart (e.g., after changing the configuration)
$ sudo systemctl stop slowdash              # stop
$ sudo systemctl disable slowdash           # disable auto-start
```

Without root privilege, it can be registered as a user service: put the file at `~/.config/systemd/user/slowdash.service` (remove the `User=` line and use `WantedBy=default.target`), then run `systemctl --user enable --now slowdash`. To keep it running while logged out and to start it at boot, `loginctl enable-linger USER` is required (ask the administrator).

## Docker
Docker containers can run in the background by design. With a restart policy, they are started automatically on failure and at boot.

```console
$ docker run -d --restart unless-stopped -p 18881:18881 -v $(pwd):/project slowproj/slowdash
```

In Docker Compose, write `restart: unless-stopped` for each service, and start with `docker compose up -d`.

| Restart policy | Behavior |
|---|---|
| `no` (default) | Not started automatically |
| `on-failure` | Restarted only when it exits with an error |
| `always` | Always restarted (even if stopped manually, it starts at boot) |
| `unless-stopped` | Always restarted (but a manually stopped container is not started at boot either) |

Docker itself must be configured to start at boot (`sudo systemctl enable docker`; this is usually enabled at installation).


# Relational Databases: PostgreSQL / MySQL / SQLite
This section is not about SQL syntax; it summarizes the differences among the three databases that matter when recording and displaying time-series data.

| | PostgreSQL | MySQL | SQLite |
|---|---|---|---|
| Form | Server | Server | A single file (no server needed) |
| Concurrent access | Many readers and writers | Many readers and writers | One writer at a time (see below). With the default settings, reads wait during writes (improved with WAL mode) |
| Suitable for | Production | Production (often already used in existing systems) | Testing, small systems (contained in a single machine). Archiving and moving data of short-term measurements |

SQLite basically assumes a single writer. In SlowDash, however, this is not an essential problem: the tasks reading out the devices can send data through SlowMesh, and a single recording task writes all of it to the database. On the other hand, SQLite has no mechanism for partitioning or replication, so PostgreSQL or MySQL should be used for systems that record large amounts of data over long periods.

Since an SQLite database is a single file, it is well suited for storing the data of short-term measurements (test runs, calibrations, each measurement run, etc.) as an archive as is, or for moving it to another machine.

- It does not depend on a database server. As long as the file exists, it can be read years later on any machine (in Python, only the standard library `sqlite3` is needed). This is an important property for preservation.
- The file format is public and stable, and the same file can be used regardless of the OS or CPU type. It is also recommended by the US Library of Congress as a format for long-term preservation.
- Copying and moving are done with ordinary file operations (`cp`, `rsync`, `scp`, etc.). SlowDash can display it just by specifying `sqlite:///FILE.db`.
- Copying a file while it is being written might produce a corrupted copy. If writing is ongoing, make a consistent copy with `sqlite3 SOURCE.db ".backup COPY.db"` or `sqlite3 SOURCE.db "VACUUM INTO 'COPY.db'"`. In WAL mode, data might remain in the files with `-wal` and `-shm` suffixes, so when copying the file itself, stop writing first.

## Connecting and Inspecting Tables

| Operation | PostgreSQL (`psql`) | MySQL (`mysql`) | SQLite (`sqlite3`) |
|---|---|---|---|
| Connect | `psql -h HOST -U USER DB` | `mysql -h HOST -u USER -p DB` | `sqlite3 FILE.db` |
| List tables | `\dt` | `SHOW TABLES;` | `.tables` |
| Table definition | `\d TABLE` | `SHOW CREATE TABLE TABLE;` | `.schema TABLE` |
| List indexes | `\di` | `SHOW INDEX FROM TABLE;` | `.indexes TABLE` |
| Show execution time | `\timing on` | always shown | `.timer on` |
| Quit | `\q` | `exit` | `.quit` |

If the database runs in Docker Compose, the client inside the container can be used (e.g., `docker compose exec postgres psql -U USER DB`). The SQLite client might need to be installed separately (`sudo apt install sqlite3`).

## Data Types

| | PostgreSQL | MySQL | SQLite |
|---|---|---|---|
| 64-bit floating point | `DOUBLE PRECISION` | `DOUBLE` (`REAL` is the same) | `REAL` |
| 32-bit floating point | `REAL` | `FLOAT` | none (all 64-bit) |
| Integer | `INTEGER` (32-bit), `BIGINT` (64-bit) | `INT` (32-bit), `BIGINT` (64-bit) | `INTEGER` (up to 64-bit) |
| String | `TEXT`, `VARCHAR(n)` | `VARCHAR(n)`, `TEXT` | `TEXT` |
| JSON | `JSONB`, `JSON` | `JSON` | `TEXT` (with JSON functions) |
| NaN, Inf | can be stored | cannot be stored | NaN becomes NULL |
| Type handling | strict | strict (strict mode, enabled by default) | loose (values of types different from the declaration can be stored) |

Notes:

- The meaning of `REAL` differs among databases. In PostgreSQL, `REAL` is 32-bit, with only about 7 significant digits. A UNIX time (about 1.7×10⁹) stored in a 32-bit float has a resolution of 128 seconds. For columns storing time as a number, use a 64-bit float (`DOUBLE PRECISION` in PostgreSQL, `DOUBLE` in MySQL) or `BIGINT`.
- In MySQL, a `TEXT` column cannot be used in an index as is (a prefix length is required). Use `VARCHAR(n)` for columns used in searches, such as channel names.

## Time and Time Zones

| | PostgreSQL | MySQL | SQLite |
|---|---|---|---|
| With time zone | `TIMESTAMP WITH TIME ZONE` (`TIMESTAMPTZ`) | `TIMESTAMP` | none |
| Without time zone | `TIMESTAMP` | `DATETIME` | date-time string in `TEXT` |
| UNIX time (numeric) | `DOUBLE PRECISION`, `BIGINT` | `DOUBLE`, `BIGINT` | `REAL`, `INTEGER` |
| Sub-second precision | microseconds | seconds by default; specify like `TIMESTAMP(6)` | depends on how it is stored |
| Check the connection time zone | `SHOW timezone;` | `SELECT @@session.time_zone;` | none |
| UNIX time → date-time | `to_timestamp(x)` | `FROM_UNIXTIME(x)` | `datetime(x, 'unixepoch')` |
| Date-time → UNIX time | `extract(epoch FROM t)` | `UNIX_TIMESTAMP(t)` | `strftime('%s', t)` |

Key points:

- Even the "with time zone" types do not store the time zone itself. On writing, the value is converted to UTC using the time zone setting of the connection; on reading, it is converted to the connection's time zone. Therefore, the same data can be displayed with different times depending on the connection settings (pointing to the same instant).
- The "without time zone" types store the given date-time as is, without recording which time zone it is in. The writer and the reader must agree on the interpretation. Around daylight-saving-time transitions, times can be duplicated or missing.
- MySQL `TIMESTAMP` can only handle times up to 2038-01-19 03:14:07 UTC (the year 2038 problem). `DATETIME` does not have this limit, but it is a type without time zone.
- MySQL `TIMESTAMP` / `DATETIME` round off sub-seconds unless a precision is specified.
- To use time zone names (such as `'Asia/Tokyo'`) in MySQL, the time zone tables must be loaded into the server. Offsets such as `'+09:00'` can always be used.
- SQLite `CURRENT_TIMESTAMP` and `datetime('now')` return UTC date-time strings.
- Recording in UNIX time (64-bit float) avoids time zone issues and the year 2038 problem, and works the same way in all three databases.

For how to specify each type in SlowDash, see [Data Binding](DataBinding.html).

## Indexes
A typical read of time-series data looks like this (the queries SlowDash issues for plots have this form):

```sql
SELECT timestamp, channel, value FROM data
WHERE channel IN ('ch00', 'ch01') AND timestamp >= START_TIME AND timestamp < END_TIME
ORDER BY timestamp;
```

A composite index on `(channel, timestamp)` is effective for this. In a composite index, put columns filtered by equality first and columns filtered by range last. With the `(timestamp, channel)` order, the data of all channels in the time range is read first and then filtered by channel, which is slow when there are many channels.

### PostgreSQL

```sql
CREATE INDEX CONCURRENTLY data_channel_timestamp ON data (channel, timestamp);
ANALYZE data;
```

- With `CONCURRENTLY`, the index is created without stopping writes (it takes longer; cannot be used inside a transaction).
- With `... ON data (channel, timestamp) INCLUDE (value)`, results can be returned from the index alone (Index Only Scan), which might be even faster. However, for a simple table like this, the index becomes a copy of the whole table, almost doubling the storage and the write load.
- For a very large table that is only appended in time order, a BRIN index is also effective (much smaller than a B-tree): `CREATE INDEX data_timestamp_brin ON data USING brin (timestamp);`

### MySQL (InnoDB)
InnoDB tables are stored in the order of the primary key (the primary key is the index of the table body itself). Therefore, making the primary key `(channel, timestamp)` is the most effective. The data of each channel is stored contiguously in time order, so reads become fast without creating another index.

```sql
-- specify at table creation
CREATE TABLE data (
    timestamp DOUBLE NOT NULL,
    channel VARCHAR(100) NOT NULL,
    value DOUBLE,
    PRIMARY KEY (channel, timestamp)
);

-- change the primary key of an existing table (the whole table is rebuilt, which takes time for large tables)
ALTER TABLE data DROP PRIMARY KEY, ADD PRIMARY KEY (channel, timestamp);
ANALYZE TABLE data;
```

If the primary key cannot be changed in an existing system, add a separate index:

```sql
CREATE INDEX data_channel_timestamp ON data (channel, timestamp);
```

In this case, after the rows are selected by the index, the table body is looked up row by row to read `value`, so it is not as fast as changing the primary key.

### SQLite
Indexes work in SQLite the same way as in the other databases.

```sql
CREATE INDEX data_channel_timestamp ON data (channel, timestamp);
ANALYZE;
PRAGMA journal_mode=WAL;
```

- With `PRAGMA journal_mode=WAL`, reads no longer wait during writes. The setting is stored in the file, so running it once is enough. It cannot be used for files on network file systems (NFS, etc.).

### Getting the Channel List
`SELECT DISTINCT channel FROM data` reads all rows as is, and becomes slow for large tables.

- MySQL and SQLite skip through an index starting with `channel`, if one exists, and process it quickly.
- PostgreSQL does not skip, so do the same with a recursive query:

```sql
WITH RECURSIVE t(channel) AS (
    SELECT MIN(channel) FROM data
  UNION ALL
    SELECT (SELECT MIN(channel) FROM data WHERE channel > t.channel) FROM t WHERE t.channel IS NOT NULL
)
SELECT channel FROM t WHERE channel IS NOT NULL;
```

In SlowDash, such a query can be given in `tags: sql:` of `time_series` (see [Data Binding](DataBinding.html)).

## Measuring Query Performance
### Checking the Execution Plan
Adding `EXPLAIN` before a query shows whether indexes are used.

| | Command | Reading all rows (slow) | Using an index |
|---|---|---|---|
| PostgreSQL | `EXPLAIN ANALYZE SELECT ...;` | `Seq Scan` | `Index Scan`, `Index Only Scan`, `Bitmap Index Scan` |
| MySQL | `EXPLAIN ANALYZE SELECT ...;` | `Table scan` | `Index range scan`, `Index lookup` |
| SQLite | `EXPLAIN QUERY PLAN SELECT ...;` | `SCAN data` | `SEARCH data USING INDEX ...` |

Example: adding an index on `(channel, timestamp)` to an SQLite table of 20 channels × 20,000 points changes the plan as follows:

```
Without index: SCAN data, USE TEMP B-TREE FOR DISTINCT             (DISTINCT: 20 ms)
With index:    SCAN data USING COVERING INDEX data_channel_timestamp (DISTINCT: less than 0.1 ms)
```

- `EXPLAIN ANALYZE` actually executes the query to measure the time (an `INSERT` or `DELETE` actually modifies the data). `EXPLAIN` alone does not execute it. MySQL `EXPLAIN ANALYZE` requires version 8.0.18 or later.
- From the second run on, the data is cached in memory and the query becomes faster, so run it several times to compare. In PostgreSQL, `EXPLAIN (ANALYZE, BUFFERS)` also shows the amount of data read from disk.
- If the statistics are outdated, an index might not be used even if it exists. Run `ANALYZE` (`ANALYZE TABLE` in MySQL) after adding a large amount of data or creating an index.

### Finding the SQL Issued by SlowDash
Starting SlowDash with `--logging=debug` prints the executed SQL to the log. Running it with `EXPLAIN ANALYZE` shows where it is slow.

```console
$ slowdash --port=18881 --logging=debug
```

### Logging Slow Queries
Queries that take longer than a specified time can be recorded in the server log:

```sql
-- PostgreSQL: log queries taking 1 second or longer
ALTER SYSTEM SET log_min_duration_statement = '1s';
SELECT pg_reload_conf();

-- MySQL: log queries taking 1 second or longer (check the log file location with SELECT @@slow_query_log_file;)
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 1;
```

### Table Size

```sql
-- PostgreSQL (in psql, \dt+ and \di+ also show sizes)
SELECT pg_size_pretty(pg_total_relation_size('data'));

-- MySQL
SELECT table_name, data_length, index_length FROM information_schema.tables WHERE table_schema = DATABASE();
```

For SQLite, the file size is the database size. In all databases, deleting data alone does not make the files smaller. To release the space, run `VACUUM FULL` in PostgreSQL, `OPTIMIZE TABLE` in MySQL, or `VACUUM` in SQLite (the table is locked while running).

## Large Data: Partitioning (PostgreSQL / MySQL)
Tables of continuous measurements only grow, and after years of accumulation the indexes become large, making both reads and writes slower. Partitioning stores a table split into smaller tables (partitions) by time range (e.g., one month). Reads and writes are done on a single table as before.

- Queries with a time range read only the relevant partitions (partition pruning; can be checked with `EXPLAIN`).
- Indexes are also split by partition. The index of the latest partition, where writes take place, stays small, so the recording speed hardly degrades as the data grows.
- Past partitions do not change, so they need to be backed up only once. In PostgreSQL, past partitions can also be moved to a large, slower disk (`ALTER TABLE data_2024_01 SET TABLESPACE archive;`).
- As a rule of thumb, consider partitioning when a table exceeds tens of GB or hundreds of millions of rows. Too many partitions (thousands or more) make query planning slow instead.
- Primary keys and unique keys must include the partitioning column (the time column). `(channel, timestamp)` can be used as is.

### PostgreSQL

```sql
CREATE TABLE data (
    timestamp TIMESTAMPTZ NOT NULL,
    channel VARCHAR(100) NOT NULL,
    value DOUBLE PRECISION,
    PRIMARY KEY (channel, timestamp)
) PARTITION BY RANGE (timestamp);

-- create a partition (the primary key and indexes of the parent table are created automatically)
CREATE TABLE data_2026_11 PARTITION OF data FOR VALUES FROM ('2026-11-01 00:00+00') TO ('2026-12-01 00:00+00');
```

- An `INSERT` of data with no matching partition results in an error. To avoid stopping the measurement, create partitions in advance (e.g., periodically with cron).
- pg_partman is an extension that automates partition creation. With TimescaleDB, an extension for time-series data, partitioning (chunks) and compression are done automatically, and the tables are read and written with ordinary SQL.
- `CREATE INDEX CONCURRENTLY` cannot be used on the parent table.

### MySQL

```sql
CREATE TABLE data (
    timestamp DATETIME(6) NOT NULL,   -- assuming writes in UTC
    channel VARCHAR(100) NOT NULL,
    value DOUBLE,
    PRIMARY KEY (channel, timestamp)
)
PARTITION BY RANGE COLUMNS (timestamp) (
    PARTITION p2026_11 VALUES LESS THAN ('2026-12-01'),
    PARTITION pmax VALUES LESS THAN (MAXVALUE)
);

-- add a new partition (split pmax)
ALTER TABLE data REORGANIZE PARTITION pmax INTO (
    PARTITION p2026_12 VALUES LESS THAN ('2027-01-01'),
    PARTITION pmax VALUES LESS THAN (MAXVALUE)
);
```

- The column types usable for partitioning are restricted. `DATETIME` and integer types can be used, but `DOUBLE` cannot (use `BIGINT` when recording in UNIX time). For `TIMESTAMP`, use `PARTITION BY RANGE (UNIX_TIMESTAMP(timestamp))`.
- With a `MAXVALUE` partition, an `INSERT` does not fail even if adding new partitions is delayed.

## Data Replication (PostgreSQL / MySQL)
Replication continuously copies writes to a database to another server (a mirror) in almost real time. In general database systems, the main purpose is to take over on server failure (availability), but this is not very important in typical SlowDash use (when the database server goes down, usually a bigger problem is happening anyway). Instead, it is used for the following purposes:

- **Protection against data loss**: always keep the recorded data on another server as well.
- **Access from remote sites**: place a mirror at another location, such as the home lab, and let remote users (and their SlowDash) connect to the mirror. This is faster, as the network link to the experiment site is not used for every access.
- **Security**: limit external access to the mirror, and do not expose the recording server to the outside. Replicate only the necessary data tables to the mirror.

### What Is Protected as a "Backup"

| How data is lost | Protected by replication? |
|---|---|
| Disk failure, loss of the server, fire, disaster | Yes (a copy exists at another location) |
| Mistaken `DELETE` or `DROP`, overwrites by program bugs | Usually not (reflected on the mirror too). However, if only appends (`INSERT`) are replicated with PostgreSQL logical replication, deletions are not reflected on the mirror |
| Restoring the state at a past point in time | Not possible. If needed, combine with periodic dumps (`pg_dump`, `mysqldump`) or file-system snapshots |

Data of continuous measurements is usually only appended, so a "remote mirror replicating only appends" is a practical backup against data loss.

### Methods

| | PostgreSQL logical replication | PostgreSQL streaming replication | MySQL replication |
|---|---|---|---|
| Unit of replication | Specified tables | Whole server (all databases, including user information) | Whole server (can be filtered on the mirror side) |
| Replicated operations | Selectable (e.g., appends only) | All | All |
| Mirror side | Ordinary database (can have its own tables and indexes) | Read-only | Ordinary database (usually set to read-only) |
| Versions of recording side and mirror | Can differ | Same major version required | Mirror must be the same or newer version |
| Suitable for | Remote mirror, external exposure | Standby within the same site | Both |

### Common Notes
- Asynchronous replication (the default) is sufficient. The mirror follows with a delay of a few seconds. With synchronous replication, writes on the recording side also stop when the mirror or the network link goes down.
- In all methods, the mirror connects to the recording server. If you do not want to expose the recording side, open an SSH tunnel from the recording side (`ssh -N -R 15432:localhost:5432 MIRROR_HOST` makes `localhost:15432` on the mirror connect to PostgreSQL on the recording side), or use a VPN. Keep the privileges of the replication user minimal, and allow only the mirror's IP address in the firewall.
- While the mirror or the network link is down, unsent update logs accumulate on the recording side, consuming disk space. The mirror catches up automatically when resumed, but do not leave it stopped for a long time.
- Changes to table definitions (`ALTER TABLE`, etc.) are not replicated by logical replication. Apply the same changes on the mirror side.

### PostgreSQL: Logical Replication (Remote Mirror)

```sql
-- recording side (set wal_level = logical in postgresql.conf and restart)
CREATE ROLE mirror WITH REPLICATION LOGIN PASSWORD '...';
GRANT SELECT ON data TO mirror;
CREATE PUBLICATION data_pub FOR TABLE data WITH (publish = 'insert');   -- replicate appends only

-- mirror side (create a table with the same definition first)
CREATE SUBSCRIPTION data_sub
    CONNECTION 'host=RECORDING_HOST port=5432 dbname=DB user=mirror password=...'
    PUBLICATION data_pub;
```

- First, all existing data is copied; after that, appends are reflected continuously.
- In `pg_hba.conf` on the recording side, allow ordinary connections to the database from the mirror's IP address (`replication` is not used for logical replication connections).
- Checking the status: `SELECT * FROM pg_stat_subscription;` on the mirror side, and `SELECT slot_name, active FROM pg_replication_slots;` on the recording side.
- On the recording side, a replication slot for the mirror is created, and update logs are kept until the mirror receives them. To avoid running out of disk space, set an upper limit with `max_slot_wal_keep_size`.
- If the table on the recording side is partitioned, `WITH (publish = 'insert', publish_via_partition_root = true)` allows the mirror side to receive the data in a single ordinary table (whether to partition on the mirror side can be decided independently of the recording side).

### PostgreSQL: Streaming Replication (Standby within the Same Site)

```console
# run on the mirror side: copy all data of the recording side and configure as a mirror (-R)
$ pg_basebackup -h RECORDING_HOST -U replicator -D /var/lib/postgresql/data -R -P
```

- Beforehand, create a replication user on the recording side (`CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD '...';`), and allow `replication` connections from the mirror in `pg_hba.conf`.
- Checking the status: `SELECT client_addr, state, replay_lag FROM pg_stat_replication;` on the recording side, and `SELECT pg_is_in_recovery();` on the mirror side (`true` for a mirror).

### MySQL

```sql
-- run on the recording side: create a replication user
CREATE USER 'replicator'@'%' IDENTIFIED BY '...';
GRANT REPLICATION SLAVE ON *.* TO 'replicator'@'%';

-- run on the mirror side (set gtid_mode=ON and enforce_gtid_consistency=ON on both the recording side and the mirror)
CHANGE REPLICATION FILTER REPLICATE_DO_TABLE = (DB.data);   -- to apply only the data table
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST='RECORDING_HOST', SOURCE_USER='replicator', SOURCE_PASSWORD='...',
    SOURCE_AUTO_POSITION=1, GET_SOURCE_PUBLIC_KEY=1;
START REPLICA;
```

- `CHANGE REPLICATION SOURCE TO` and `START REPLICA` are the syntax for version 8.0.23 and later (before that, `CHANGE MASTER TO` and `START SLAVE`). `GET_SOURCE_PUBLIC_KEY=1` is required to connect with the default authentication method of MySQL 8 without SSL.
- Set a different `server_id` on the recording side and on the mirror. Copy the existing data to the mirror beforehand with `mysqldump` or the clone plugin.
- Table filtering (`REPLICATE_DO_TABLE`) is done on the mirror side. The update logs of all tables are sent from the recording side, so this is not suitable when you want to limit the data leaving the site itself. Also, all operations, including deletions, are applied.
- Checking the status: `SHOW REPLICA STATUS\G` on the mirror side. `Replica_IO_Running` and `Replica_SQL_Running` should be `Yes`, and `Seconds_Behind_Source` shows the delay in seconds.
- Set `super_read_only=ON` on the mirror to prevent accidental writes.
- The retention period of the update logs (binlog) on the recording side is `binlog_expire_logs_seconds` (30 days by default). If the mirror is stopped longer than this, it has to be copied again from scratch.


# Docker
SlowDash can be used without Docker. With Docker, SlowDash and databases can run without preparing a Python environment on the host.

| Term | Meaning |
|---|---|
| Image | A bundle of the runtime environment (OS files, libraries, programs). E.g., `slowproj/slowdash`, `postgres:16`. The part after `:` is the tag (version) |
| Container | A running instance started from an image |
| Volume / bind mount | A mechanism to keep data outside the container. It remains after the container is removed |
| Port publishing | Forwarding a host port to a container port |

## docker run

```console
$ docker run --rm -p 18881:18881 -v $(pwd):/project slowproj/slowdash
```

| Option | Meaning |
|---|---|
| `-p HOST:CONTAINER` | Forward a host port to a container port |
| `-v HOST_PATH:CONTAINER_PATH` | Mount a host directory into the container (absolute path on the host side) |
| `-v NAME:CONTAINER_PATH` | Mount a named volume (data stored in an area managed by Docker) |
| `-e NAME=VALUE` | Set an environment variable |
| `--rm` | Remove the container automatically when stopped |
| `-d` | Run in the background |
| `--name NAME` | Name the container |
| `-it` | Run interactively (when using a shell) |

## Frequently Used Commands

```console
$ docker ps                       # list running containers (-a to include stopped ones)
$ docker logs -f CONTAINER        # show logs (-f to follow)
$ docker exec -it CONTAINER bash  # start a shell in a running container
$ docker stop CONTAINER
$ docker rm CONTAINER
$ docker images                   # list local images
$ docker pull IMAGE:TAG           # get or update an image
$ docker rmi IMAGE                # remove an image
$ docker system prune             # remove stopped containers, unused images, etc. at once
```

## Common Pitfalls
- On Linux, the `docker` command requires root privilege. Either add `sudo` every time or add the user to the `docker` group (`sudo usermod -aG docker $USER`, then log in again). Note that users in the `docker` group effectively have root privilege.
- `localhost` inside a container refers to the container itself. To connect to a database or other services running on the host, use `host.docker.internal` (on Linux, `--add-host=host.docker.internal:host-gateway` is required).
- Ports published with `-p` bypass the ufw firewall rules and are reachable from outside (see [Docker and ufw](#docker-and-ufw)).
- If the process in a container runs as root, files created in a bind-mounted directory are owned by root on the host (e.g., when a database data directory is bind-mounted).
  - The SlowDash container checks the owner (UID / GID) of the mounted `/project` directory at startup, and runs SlowDash as a user with the same IDs. Therefore, files created by SlowDash are owned by the owner of the project directory. The IDs can also be given explicitly with the environment variables `USER_ID` and `GROUP_ID`.
  - However, a shell entered with `docker exec` runs as root, so files created there are owned by root. To run as the same user as SlowDash, use `docker exec -it -u slowuser CONTAINER bash`.

## Updating Images and Removing Old Ones
Tags such as `:latest` are not updated automatically. To use a new version, pull the image with `docker pull` (`docker compose pull` in Compose), and then restart the container.

`docker pull` does not remove old images. The new image takes over the tag, and the old image remains untagged (`<none>`), so repeated updates fill up the disk.

```console
$ docker images                   # list images; those tagged <none> are old images
$ docker system df                # disk usage of images, containers, and volumes
$ docker image prune              # remove all untagged images
$ docker image prune -a           # remove all images not used by containers (they will be pulled again when needed)
$ docker rmi IMAGE_ID             # remove individually (IMAGE_ID is shown by docker images)
```

Images used by stopped containers cannot be removed. Check with `docker ps -a`, remove unnecessary containers with `docker rm`, and then remove the images.


# Docker Compose
A mechanism to describe a configuration of multiple containers (e.g., SlowDash and a database) in `docker-compose.yaml`, and to start and stop them together.

## docker-compose.yaml

```yaml
services:
  postgres:                              # service name (other containers can access it by this name)
    image: postgres:16
    environment:
      - POSTGRES_USER=slowdash
      - POSTGRES_PASSWORD=slowdash
    volumes:
      - postgres-data:/var/lib/postgresql/data   # named volume
    healthcheck:                         # how to determine that startup is complete
      test: ["CMD-SHELL", "pg_isready -U slowdash"]
      interval: 10s
      retries: 5
    restart: unless-stopped              # restart automatically on failure or host reboot

  slowdash:
    image: slowproj/slowdash
    ports:
      - "18881:18881"
    volumes:
      - ./slowdash.d:/project            # bind mount (relative paths are from the location of docker-compose.yaml)
    environment:
      - DB_URL=postgresql://slowdash:${DB_PASSWORD:-slowdash}@postgres:5432/slowdash
    depends_on:
      postgres:
        condition: service_healthy       # start after the postgres healthcheck passes
    restart: unless-stopped

volumes:
  postgres-data:
```

Key points:

- Services in the same `docker-compose.yaml` can communicate using service names as host names (`postgres:5432` in the example above). `ports` is needed only for connections from the host.
- `${VAR}` and `${VAR:-DEFAULT}` are expanded from shell environment variables or from the `.env` file in the same directory. It is common to write passwords etc. in `.env` and not to put `.env` in git.
- `depends_on` controls only the startup order. To wait until the other service is ready, combine `condition: service_healthy` with `healthcheck`.

## Frequently Used Commands
Run in the directory containing `docker-compose.yaml`:

```console
$ docker compose up               # start (Ctrl-C to stop)
$ docker compose up -d            # start in the background
$ docker compose ps               # show status
$ docker compose logs -f SERVICE  # show logs
$ docker compose exec SERVICE bash
$ docker compose restart SERVICE
$ docker compose down             # stop and remove containers (named volumes remain)
$ docker compose down -v          # also remove named volumes (database data is lost)
$ docker compose pull             # update images (apply with up; remove old images with docker image prune)
$ docker compose up --build       # rebuild images specified by build: and start
$ docker compose config           # show the configuration after variable expansion (useful for checking)
```

`docker-compose` (with a hyphen) is the old command, which is no longer supported. Use `docker compose` (with a space) now.


# Docker Swarm
A mechanism to deploy and manage containers across multiple hosts. It is included in Docker and uses files of almost the same format as `docker-compose.yaml`. For running on a single host, Docker Compose is sufficient. Swarm is useful, for example, when you want to:

- deploy SlowDash, databases, device readers, etc. on multiple hosts and manage them with a single configuration file
- access services with the same port from any host
- manage passwords etc. as secrets

## Setting Up a Cluster

```console
manager$ docker swarm init --advertise-addr MANAGER_IP   # create a cluster on the manager node
manager$ docker swarm join-token worker                  # show the command for adding workers
worker$  docker swarm join --token TOKEN MANAGER_IP:2377 # run on worker nodes
manager$ docker node ls                                  # list nodes
```

TCP 2377, TCP/UDP 7946, and UDP 4789 must be open between the nodes.

## Deploying a Stack
In Swarm, a set of services defined in `docker-compose.yaml` is deployed as a "stack". Run the commands on a manager node.

```console
$ docker stack deploy -c docker-compose.yaml STACK      # deploy (the same command re-applies changes)
$ docker stack ls
$ docker stack services STACK                           # services and their replica counts
$ docker stack ps STACK                                 # which node each container runs on
$ docker service logs -f STACK_SERVICE                  # service names are STACK-NAME_SERVICE-NAME
$ docker service update --force STACK_SERVICE           # restart a service
$ docker stack rm STACK                                 # remove the stack
```

## Differences from Compose

```yaml
services:
  slowdash:
    image: slowproj/slowdash
    ports:
      - "18881:18881"
    volumes:
      - /srv/slowdash/project:/project
    deploy:                              # effective only in Swarm
      replicas: 1
      placement:
        constraints:
          - node.hostname == daq-server  # run on this node
```

- The `deploy:` section becomes effective (number of replicas, placement nodes, restart policy, etc.).
- `build:` is ignored. Images must be available from a registry or exist on each node beforehand.
- `depends_on` is ignored. The startup order is not guaranteed, so each service must retry until the services it connects to are ready (by default, Swarm restarts exited containers automatically).
- The host-side path of a bind mount must exist on the node where the container actually runs. For services using data or project directories, pinning the node with `placement` is the simplest.
- Ports published with `ports` are accessible via the IP of any node in the cluster (routing mesh).
- The `.env` file is not read automatically. If variable expansion is needed, load it in the shell beforehand (`set -a; source .env; set +a`).
- Stateful services such as databases and SlowDash are usually set to `replicas: 1`.


# References
- YAML: [yaml.org](https://yaml.org/)
- venv: [Python documentation](https://docs.python.org/3/library/venv.html)
- pyenv: [GitHub](https://github.com/pyenv/pyenv)
- PostgreSQL: [Documentation](https://www.postgresql.org/docs/)
- MySQL: [Reference Manual](https://dev.mysql.com/doc/refman/8.4/en/)
- SQLite: [Documentation](https://www.sqlite.org/docs.html)
- Docker / Docker Compose / Docker Swarm: [Docker Docs](https://docs.docker.com/)
