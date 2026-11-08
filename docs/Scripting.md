---
title: Scripting
---

# Overview

SlowDash is a hybrid system of a Web GUI and Python scripting.
A system is built by attaching Python code, which describes the behavior, behind the display elements of the Web GUI.

The Python scripts written by users here are plain standard Python, and can use existing systems and any external libraries.
Functions in a script are bound to the Web GUI, but the binding is specified on the GUI side (the GUI specifies the name of the function in the user script to be called on an action), so the user script itself does not need to use the SlowDash framework or libraries at all.

On the other hand, the features of SlowDash can also be used more actively.
In many cases, just by adding a one-line decorator to a user function, more advanced bindings, including concurrent / parallel execution control, become available, and periodic execution, execution at start-up, etc. can be done easily.

SlowDash provides SlowPy, a library that implements functions frequently used in user scripts, such as device access.
Using SlowPy is optional, but it makes many things easier.
SlowPy itself can be used without the SlowDash server, and user scripts using SlowPy can also run standalone without the SlowDash server, as long as they do not use SlowMesh communication.

A user script running as a part of a SlowDash system is called a SlowTask. A SlowTask usually runs as an independent process.
A SlowTask can be started automatically together with the SlowDash server, or can be started and stopped independently of the server, for example with Docker Compose.

By running user scripts within the SlowDash framework using SlowPy, multiple SlowTasks can work cooperatively through message passing, remote function calls, parameter sharing, etc. (SlowMesh).
In a system of some size, it is common for multiple SlowTasks to run in parallel, and SlowTasks can even be distributed over a network without changing the scripts.
SlowTask processes work exactly the same way when they are managed by another system such as Docker Swarm or Kubernetes, instead of the SlowDash distributed processing features.
Some SlowTask scripts, such as database recording, are included in the SlowDash distribution package as general-purpose components (SlowTools), and a system can be built by combining them.

An example of running multiple SlowTasks on SlowMesh is in the [Quick Tour](QuickTour.html), which can be tried out in a disposable environment that can be cleanly thrown away after use.
This chapter describes the details of building a system by writing SlowTask scripts with SlowPy.

# SlowPy Library
## Structure
The SlowPy library is located at `slowdash/lib/slowpy` in SlowDash, separated from the SlowDash server and the Web GUI (under `slowdash/app`).
The SlowPy package consists of the following sub-packages.
Everything can be imported at once with `import slowpy`, but sub-package names must be used when referring to them, as in `slowpy.control.XXX`.
Alternatively, `import slowpy.control` or `from slowpy.control import XXX` can also be used.

| Name | Role | External Dependency |
|---|---|---|
| control | Controlling devices and external control systems | Vendor-provided libraries (if any) |
| (top level) | Data analysis components such as histograms | - |
| store   | Data recording | The database system used |
| mesh    | SlowMesh communication | SlowDash server |

Analysis components such as histograms are at the top level of `slowpy`, and are used like `slowpy.Histogram`.

The SlowDash server is required to run a user script only if the script actually communicates using `slowpy.mesh`.
Otherwise, the script can run standalone, independently of SlowDash.
This is convenient for script development.
In the standard SlowDash installation, the SlowPy library is installed in a venv, so activate the venv before using it standalone.
This is not necessary when running as a SlowTask from the SlowDash server.
```console
$ slowdash-activate-venv    # (or, source PATH/TO/SLOWDASH/venv/bin/activate)
```

SlowPy corresponding to a SlowDash release can also be installed with pip.
This might be useful when using SlowPy on a PC that only does analysis.
Note that SlowPy on pip is updated only when SlowDash is tagged for a release, so it might be outdated.
```console
$ pip install slowpy
```

## Simple Examples
#### Reading a measured value from an Ethernet-connected voltmeter with an SCPI command
```python
from slowpy.control import control_system as ctrl

# Create a control node for SCPI command "MEAS:VOLT:DC" on a device at 192.168.1.43
V = ctrl.ethernet('192.168.1.43', 5025).scpi().command('MEAS:VOLT:DC')

while True:
  # Read a value from the control node using SCPI command "MEAS:VOLT:DC?"
  value = V.get()
  ...
```

#### Recording data into a PostgreSQL database
```python
from slowpy.store import DataStore_PostgreSQL

datastore = DataStore_PostgreSQL('postgresql://postgres:postgres@localhost:5432/SlowTestData', table="SlowData")

while True:
    value = ...
    datastore.append(value, tag="voltmeter")
```

#### Calling a function from the SlowDash Web GUI
Output voltage setting function `set_Vout()` in script `config/slowtask-test.py`:
```python
from slowpy.control import control_system as ctrl
Vout = ctrl.ethernet('192.168.1.43', 5025).scpi(append_opc=True).command('VOLT')

def set_Vout(value:float):
    Vout.set(value)
```
User-created HTML for the Web GUI (`config/html-test.html`):
```html
<form>
  Voltage output: <input name="value">
  <button name="test.set_Vout()">Set</button>
</form>
```
When the `Set` button is clicked on the browser, the value in the `<input name="value">` field is converted to float, and `set_Vout(value)` is called with it as the argument.

##### A small improvement, part 1
Both normal functions and async functions can be used. Making the function async lets it run concurrently with other processing, improving the overall responsiveness.
```python
async def set_Vout(value:float):
    await Vout.aio_set(value)
```

##### A small improvement, part 2
With `Tasklet`, which controls a SlowTask in SlowPy, the functions to be called from the browser can be explicitly specified.
```python
from slowpy.mesh import Tasklet
tasklet = Tasklet()

@tasklet.mesh.export()
async def set_Vout(value:float):
    await Vout.aio_set(value)
```

#### Reading data every second and streaming it to the browser
```python
from slowpy.mesh import Tasklet
tasklet = Tasklet()

from slowpy.control import control_system as ctrl

device = ctrl.ethernet('192.168.1.43', 5025).scpi()
V = device.command('MEAS:VOLT:DC')
A = device.command('MEAS:CURR:DC')

@tasklet.loop(interval=1.0)
def loop():
    ctrl.stream('voltage', V.get())
    ctrl.stream('current', A.get())
```

##### A small improvement
As above, using async improves the performance.
```python
@tasklet.loop(interval=1.0)
async def loop():
    await ctrl.aio_stream('voltage', await V.aio_get())
    await ctrl.aio_stream('current', await A.aio_get())
```

## Controls
### Node Tree Structure
SlowPy provides a unified interface to connect to external software systems and hardware devices.
Everything is mapped into a single "control tree", and each node of the tree has `set()` and `get()` methods.
The tree represents the logical structure of the system.
For example, the SCPI command `VOLT` to a power supply connected via Ethernet is specified as `ControlSystem.ethernet(host, port).scpi().command('VOLT')`, and calling `set(value)` on this node sends the SCPI command `VOLT value` to the device.
The `get()` method performs a read operation and returns the value.

Branches can be dynamically added to the control tree by plugin modules.
For example, the Redis plugin adds a `redis()` node and several sub-branches corresponding to the features provided by Redis, such as hashes, JSON, and time-series.
Plugins are not necessarily loaded to the root ControlSystem; they are loaded to any node.
For example, a plugin that uses Ethernet is loaded to the Ethernet node and creates branches under it, and the plugin can use the functions provided by the Ethernet node, such as `set()` (send) and `get()` (receive).

#### Example
Here is an example of using SlowPy Controls. In this example, a power supply that accepts SCPI commands over Ethernet is used.

```python
from slowpy.control import control_system as ctrl

# Create a control node for SCPI command "VOLT" (output) and "MEAS:VOLT:DC" (readback) on a device at 192.168.1.43
device = ctrl.ethernet('192.168.1.43', 5025)
Vout = device.scpi(append_opc=True).command('VOLT')
V = device.scpi().command('MEAS:VOLT:DC')

# Write a value to the control node: this will issue SCPI command "VOLT 10;*OPC?"
Vout.set(10)

while True:
  # Read a value from the control node using SCPI command "MEAS:VOLT:DC?"
  value = V.get()
  ...
```
Usually, as in this example, start by directly importing the instance `control_system` from `slowpy.control`.
(It is also fine to import the `ControlSystem` class and create an instance yourself.)

`ControlSystem` already includes the `Ethernet` plugin, but if it did not, the code to load the plugin would be:
```python
ctrl.import_control_module('Ethernet')
```
This searches the search directories (the current directory and the SlowPy directory) for a file named `control_Ethernet.py` and loads it, adding the `ethernet()` method to the class of the node to which the plugin is loaded (ControlSystem in this case).
As `import_control_module()` returns the node itself, it can be chained like `ctrl.import_control_module('DummyDevice').randomwalk_device()`.
The Ethernet plugin already includes the SCPI and Telnet branches. To use other specific protocols, load a plugin for it to the Ethernet node.

The constructor of each node takes parameters.
In this example, the Ethernet node, which sends and receives data over Ethernet, takes the host name (IP address) and the port number as parameters.
The SCPI command node, which is bound to a specific SCPI command, takes the SCPI command as a parameter, and optionally `set_format` to change the command on writing.
(For `.scpi().command(CMD)`, the command sent on writing is `CMD value` by default, and `CMD?` on reading.)

SlowPy assumes that every SCPI command has a response.
In many cases, write operations also need to wait for the command to complete.
One way to achieve this regardless of the actual command behavior of the device is to append `*OPC?` to the command, as in the example.
With `scpi(append_opc=True)`, `*OPC?` is appended to every `set()` under that node. (It is not appended to `get()`, which already has a response.)
To switch it per command, `*OPC?` can be appended to the command manually, like `command('OUTP ON;*OPC?')`.

Once a control node object is obtained, a value can be written with `node.set(value)` and read with `value = node.get()`.

Whether a new connection is made or the same one is reused when a connection node (such as `ethernet()`) is called multiple times depends on the node type and parameters.
Usually, as in the example, it is convenient to create a device-level node once and store it in a variable.

### Async Interface
When SlowDash runs a user script as a SlowTask, unless explicitly specified, it runs as a single-threaded async system, where everything is processed concurrently using async.
Therefore, if a user function takes a long time to execute, the whole system freezes.
It is recommended to implement user script functions as async, and to call the async versions of SlowPy node methods with `await` for time-consuming operations in them.
```python
async def set_Vout(value:float):
    await Vout.aio_set(value)
```

For this purpose, async versions are provided for almost all methods of SlowPy nodes.
Their names have the prefix `aio_` added to the names of the normal functions (`set()`/`get()` etc.), as in `aio_set()`/`aio_get()`.

Many SlowPy devices implement both `set()`/`get()` and `aio_set()`/`aio_get()`, but which ones are actually available depends on the device.
If only `set()` is implemented and there is no `aio_set()`, a call to `await aio_set()` either goes through `asyncio.to_thread()` (if thread safety is explicitly declared), or falls back directly to `set()` (with a possibility of starvation).
Whether a node is thread-safe is stored in the `_is_thread_safe` member variable of the `ControlNode` base class.

Blocking functions such as `sleep()` and `wait()` also have async versions such as `aio_sleep()` and `aio_wait()`.
In a SlowTask, use `await ctrl.aio_sleep()` instead of `time.sleep()` or `ctrl.sleep()`.

### Threads and Async Tasks of Control Nodes
Some control nodes run in the background, independently of `set()` and `get()` calls. For example:

- Nodes that run a task independently of `set()`/`get()` queries, such as PID loops and ramping
- Nodes that periodically pre-fetch data and store it in a cache, when data acquisition takes time

Such nodes are implemented by inheriting `ControlThreadMixin` or `ControlAsyncTaskMixin`.

- `ControlThreadMixin`: If the node has a `run()` method, calling `start()` creates a dedicated thread, in which `run()` is executed.
- `ControlAsyncTaskMixin`: If the node has an `async def aio_run()` method, calling `start()` creates an asyncio task, which executes `aio_run()`.

The threads and tasks are stopped by calling the node's `stop()` method, or by a global stop request (`ControlSystem.stop()`, signals, etc.).
The `run()` function must monitor stop requests (with `is_stop_requested()`) and terminate by itself when a stop is requested.
In the case of `aio_run()`, the task is cancelled by `stop()` and stops at the next `await`.

For example, `first_order_plant` of the dummy device is a node that runs a simulation in a thread, and is used like this:
```python
plant = ctrl.import_control_module('DummyDevice').first_order_plant(gain=0.1, noise=0.1)
plant.start()

while True:
    state = plant.get()   # time-evolved internal state
    ...
```

### Commonly Used Nodes
Naming convention: `set()`, `get()`, and `do_XXX()` are normal methods that perform actions. Methods with noun names return child nodes.

#### Ethernet, SCPI, Telnet
##### Loading (built-in)
`ctrl.import_control_module('Ethernet')`

##### Nodes
- **ethernet(host, port)**: sends and receives text messages over a TCP socket connection
  - set(value): sends the value as encoded text
  - get(): receives a chunk of text
  - do_get_chunk(timeout=None): receives a chunk of text
  - do_get_line(timeout=None): receives chunks and returns one line (reassembled if necessary)
  - do_flush_input(): empties the receive buffer
  - **scpi(timeout=10, line_terminator='\x0d', append_opc=False)**: bridges the parent Ethernet connection to SCPI, and holds the SCPI settings
    - **command(cmd, set_format=None)**: issues an SCPI command over the parent Ethernet connection
      - set(value=None): sends `cmd value` and waits for the response
      - get(): sends `cmd?`, waits for the response, and returns it
  - **telnet(prompt, line_terminator)**: bridges the parent Ethernet connection to Telnet, and holds the Telnet settings
    - **command(cmd)**: issues a Telnet command over the parent Ethernet connection
      - set(value=None): sends `cmd value NEWLINE`, and discards the echo
      - get(): sends `cmd NEWLINE`, discards the echo, and returns the response up to the next prompt

#### Serial Port
##### Loading
`ctrl.import_control_module('Serial')` (requires the `pyserial` package)

##### Nodes
- **serial(port='/dev/ttyUSB0', baudrate=115200)**: sends and receives text messages over a serial port
  - set(value): sends the value as encoded text
  - get(): receives a chunk of text
  - do_get_chunk(timeout=None): receives a chunk of text
  - do_get_line(timeout=None): receives chunks and returns one line (reassembled if necessary)
  - do_flush_input(): empties the receive buffer
  - **scpi()**: same as `scpi()` of the Ethernet node

#### VISA
Devices connected via USB, GPIB, HiSLIP, etc. can be used through VISA.
##### Loading
`ctrl.import_control_module('VISA')` (requires the `pyvisa` package)

##### Nodes
- **visa(resource_name)**: device specified by a VISA resource name (e.g., `USB0::0x2A8D::0x0201::MY54700218::0::INSTR`)
  - **scpi()**: same as `scpi()` of the Ethernet node

#### HTTP (Web API)
##### Loading (built-in)
`ctrl.import_control_module('HTTP')`

##### Nodes
- **http(base_url)**:
  - **path(path)**: path string appended to `base_url`
    - set(value): sends a POST request with `value` as the content to `base_url` + `path`
    - get(): sends a GET request to `base_url` + `path`, and returns the response content
    - **json()**: 
      - set(value): `value` is a Python object to be converted to JSON
      - get(): receives a JSON document and returns it as a Python object
    - **value()**: returns a ControlVariableNode, to be used with ramping() etc.

An async version, `async_http(base_url)`, is also built in.

#### Shell Command
##### Loading (built-in)
`ctrl.import_control_module('Shell')`

##### Nodes
- **shell(cmd)**: executes a shell command
  - set(value): launches `cmd value`
  - get(): launches `cmd` and returns its output
  - **value()**: returns a ControlVariableNode, to be used with ramping() etc.
  - **arg(\*args)**: adds program arguments to the parent "shell" node <br>
    Example: `adc0 = ctrl.shell('read_adc').arg('--ch=0')`
    - **value()**: returns a ControlVariableNode, to be used with ramping() etc.
    
#### Accessing the SlowDash Server
##### Loading
Load to an HTTP node: `ctrl.http(url).import_control_module('Slowdash')`

##### Nodes
- **http(url).slowdash()**
  - **ping()**: returns `pong`
  - **channels()**: gets the JSON object of the channel list
  - **data(channels, length=3600)**: gets the JSON object of the data of the specified channels
  - **config()**: gets the JSON object of the project configuration
  - **config_file(name)**: gets or sends a configuration file

As an async version, there is also the `AsyncSlowdash` plugin (`async_slowdash()`), which is loaded to `async_http(url)`.
  
#### Other Nodes (excerpt)
- Redis (uses the `redis` package)
- RabbitMQ (uses `pika` and `aio-pika`)
- MQTT (uses `paho-mqtt` and `aio-mqtt`)
- NATS (uses `nats-py`)
- Modbus (uses `pymodbus`)
- LabJack (uses `LabJackPython`; currently only U3/U6/U12 are supported)
- UDP
- DataStore (`set()` to `data_store(url).tag(name)` records the value into the database)
- DummyDevice (dummy devices for testing, such as random walks, event generators, and first/second-order lag plants)

SlowPy control plugins are placed under `slowdash/lib/slowpy/slowpy/control` with names like `control_XXX.py`.
For usage examples, see the test scripts under `slowdash/lib/slowpy/test`.

### Common Node Functions
All control nodes (classes derived from `slowpy.control.ControlNode`) have the following methods.

- [ControlNode]
  - **has_data()**: returns True if there is a value that can be obtained with `get()`
  - **wait(condition_lambda=None, poll_interval=0.1, timeout=0)**: If `condition_lambda` is not None, blocks until `condition_lambda` returns `True`. If `condition_lambda` is None, waits until `has_data()` returns True. Returns `None` on timeout, `False` if a stop is requested, and `True` otherwise.
  - **sleep(duration_sec)**: blocks for the specified duration. Returns True unless a stop request is received.
  - **is_stop_requested()**: returns True if a stop request has been received
  - **snapshot()**: returns a node that holds the value obtained by `get()` and returns the same value to `get()` of its child nodes (used, for example, to extract each field of data obtained by a single read through child nodes)

`wait()` and `sleep()` also have async versions, `aio_wait()` and `aio_sleep()`.

Nodes derived from `ControlVariableNode` have the following methods.

- [ControlVariableNode] -> [ControlNode]
  - **setpoint(limits=(None,None))**: holds a setpoint
    - set(value): holds the value as the setpoint and calls `set(value)` of the parent node. Raises an exception if the value is outside the limits.
    - get(): returns the held setpoint value
  - **ramping(change_per_sec)** / **async_ramping(change_per_sec)**: sets the value while ramping it (thread version / async task version)
    - set(value): starts ramping the parent node's value toward the target value. Raises an exception if the value is not numeric.
    - get(): returns `get()` of the parent node
    - **status()**
      - set(value): `set(0)` stops the ongoing ramping
      - get(): returns `True` if ramping is in progress, `False` otherwise
  - **pid(sensing_node, Kp, Ki, Kd, \*, interval=1.0, output_limits=(None,None))**: PID-controls this node using the value read from `sensing_node`
    - set(value): starts a PID loop so that the value of the sensing node becomes the target value. `set(None)` stops the control.
    - get(): returns the target value
    - **status()**
      - set(value): `set(0)` stops the PID loop
      - get(): returns a dict containing various control parameters (`running`, `setpoint`, `measurement`, `output`, `Kp`, `Ki`, `Kd`, etc.)
  - **oneshot(duration=None, normal=None)**: holds the value set with `set()` for the specified duration, and then reverts it to the `normal` value
  - **readonly()**: makes the node read-only. Returns a node that only has `get()`, which calls `get()` of the parent node. (Useful when exposing a node externally.)
  - **writeonly()**: makes the node write-only. Returns a node that only has `set()`, which calls `set()` of the parent node.

Nodes that inherit `ControlThreadMixin` or `ControlAsyncTaskMixin` have the following methods.

- [ControlThreadMixin / ControlAsyncTaskMixin]
  - **start()**: creates and starts `run()` (thread) or `aio_run()` (async task)
  - **stop()**: stops the thread or task


## Database Interface
With the SlowPy DataStore, data can be recorded into a database in a format that SlowDash can read.
Here is a simple example of writing single values into a long-format table.
```python
from slowpy.control import control_system as ctrl
from slowpy.store import DataStore_PostgreSQL

device = ctrl.import_control_module('DummyDevice').randomwalk_device()
datastore = DataStore_PostgreSQL('postgresql://postgres:postgres@localhost:5432/SlowTestData', table="Test")

while True:
    for ch in range(4):
        value = device.ch(ch).get()
        datastore.append(value, tag='%02d'%ch)

    ctrl.sleep(1)
```

The following DataStore classes are available.

| Class | URL Format | Notes |
|---|---|---|
| `DataStore_SQLite` | `sqlite:///FILE_NAME` | The second argument is the table name |
| `DataStore_PostgreSQL` | `postgresql://USER:PASS@HOST:PORT/DB` | The second argument is the table name |
| `DataStore_MySQL` | `mysql://USER:PASS@HOST:PORT/DB` | The second argument is the table name |
| `DataStore_InfluxDB2` | `influxdb2://ORGANIZATION:TOKEN@HOST:PORT/BUCKET` | The second argument is the measurement name |
| `DataStore_Redis` | `redis://HOST:PORT/DB` | |
| `DataStore_HDF5` | (file name) | The second argument is the dataset name. For per-run file recording, etc. |
| `DataStore_CSV` | `csv:///FILE_NAME` | |

There is also a function, `create_datastore_from_url(url, table)`, which creates an appropriate DataStore from a URL. This is useful when the database URL is given from a configuration file, etc.
```python
from slowpy.store import create_datastore_from_url
datastore = create_datastore_from_url('sqlite:///SlowStore.db', 'slowdata')
```

The main methods of DataStore are:

- **append(values, tag=None, timestamp=None)**: adds the values as time-series data
- **update(values, tag=None, timestamp=None)**: updates the values (only the latest values are kept)
- **another(table)**: returns a DataStore that writes into another table of the same database (SQL only)
- **close()**: closes the connection to the database

In addition to numbers and strings, analysis objects such as histograms (described later) can be passed as `values`.
`timestamp` is in UNIX time; if omitted, the current time is used.

For SQL databases, the "long format" with UNIX timestamps (`(timestamp REAL, channel VARCHAR(100), value REAL)`) is used by default.
To use other table schemas, specify a user-defined `TableFormat`.
```python
from slowpy.store import DataStore_SQLite, LongTableFormat

class MyDataFormat(LongTableFormat):
    schema_numeric = '(datetime DATETIME, timestamp INTEGER, channel VARCHAR(100), value REAL, PRIMARY KEY(timestamp, channel))'
    schema_text = '(datetime DATETIME, timestamp INTEGER, channel VARCHAR(100), value TEXT, PRIMARY KEY(timestamp, channel))'

    def insert_numeric_data(self, cur, timestamp, channel, value):
        ph = self.db.placeholder
        cur.execute(f'INSERT INTO {self.table} VALUES(CURRENT_TIMESTAMP,{ph},{ph},{ph})', (int(timestamp), channel, value))

    def insert_text_data(self, cur, timestamp, channel, value):
        ph = self.db.placeholder
        cur.execute(f'INSERT INTO {self.table} VALUES(CURRENT_TIMESTAMP,{ph},{ph},{ph})', (int(timestamp), channel, str(value)))

datastore = DataStore_SQLite('sqlite:///MySlowStore.db', table="slowdata", table_format=MyDataFormat())
```

When recording data from multiple SlowTasks, instead of having each task write directly into the database, it is convenient to publish the data to SlowMesh and have a single SlowTask dedicated to recording write it all into the database (see the SlowMesh section below).
This avoids conflicts even with databases that have limitations on concurrent writes, such as SQLite, and also keeps the table schema description in one place.

## Analysis Components
SlowPy provides commonly used data objects such as histograms and graphs.
These objects can be written directly into a database using the SlowPy database interface described above.
They can also be sent directly to the browser without going through a database, using the streaming feature described later.

### Histogram
```python
import slowpy
hist = slowpy.Histogram(nbins=100, range_min=0, range_max=10)

device = ...
datastore = ...

while True:
  value = device.read(...
  hist.fill(value)

  if time_to_store:
    datastore.append(hist, tag="test_hist")
  ...
```

`datastore.append(hist, tag=name)` creates a time series of histograms (one histogram per time point).
To keep only the latest histogram, use `datastore.update(hist, tag=name)` instead.

The contents of a histogram can be cleared with `clear()`.
Also, with `add_stat()`, statistics such as the number of entries and the mean can be attached to the histogram for display.
```python
hist.add_stat(slowpy.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))
```
There is also a 2D histogram, `Histogram2d(xnbins, xrange_min, xrange_max, ynbins, yrange_min, yrange_max)`.

### Graph
```python
import slowpy
graph = slowpy.Graph(['channel', 'value'])

while True:
  for ch in range(n_ch):
    value = device.read(ch, ...
    graph.fill(ch, value)
  if time_to_store:
    datastore.append(graph, tag="test_graph")
  ...
```

`datastore.append(graph, tag=name)` creates a time series of graphs (one graph per time point).
To keep only the latest graph, use `datastore.update(graph, tag=name)` instead.
Like histograms, graphs also have `add_stat()`.

### Trend
A Trend is a special graph that divides data into time bins and calculates the mean, etc. for each bin.
There is the normal Trend, which holds the mean, etc. of data values, and the RateTrend, which is specialized for holding the number of data entries (rate).

```python
import slowpy
rate_trend = slowpy.RateTrend(length=300, tick=10)

while True:
  value = device.read(...
  rate_trend.fill(time.time())

  if time_to_store:
    datastore.append(rate_trend.timeseries())
    rate_trend.flush()
```

Unlike Histogram and Graph, a Trend is not recorded as a single object into a database; instead, it is expanded into time-series data.
The `timeseries()` method is used for this.
(It is possible to store the Trend object itself, but this is usually not done.)
Also, `flush()` is called after recording, to delete the part of the data already recorded in the database. (`timeseries(flush=True)` does the same.)

When streaming to the browser, all of the held past data should be displayed, so do not `flush()`, and send the entire result of `timeseries()` every time.
```python
await ctrl.aio_stream('rate_trend', rate_trend.timeseries())
```

## Making a Device SCPI-Capable
If a device has some programming capability, such as the GPIO of a Raspberry Pi, a simple way to integrate it into a SlowDash system is to implement an SCPI interface on the device.
This approach is also useful for integrating non-Ethernet devices (such as USB) connected to a remote computer, via a Raspberry Pi or similar.

Here is an example of wrapping a device with Ethernet SCPI.

```python
from slowpy.control import ScpiServer
scpi = ScpiServer()

class MyMemoryDevice:
    def __init__(self):
        self.value = 0
device = MyMemoryDevice()

@scpi.on('*IDN?')
def get_idn():
    return 'MyMemoryDevice'

@scpi.on('Volt')
def set_V(value:float):
    device.value = value
    
@scpi.on('MEASure:Volt?')
def get_V():
    return device.value

scpi.start(port=5025)
```

This implements the following SCPI commands (commands are case-insensitive):

| Command | Action | Command Example | Return Example |
|---|---|---|---|
| `*IDN?` | Returns the device ID | `*IDN?` | `MyMemoryDevice` |
| `Volt <Value>` | Sets the value | `V 10` | (none) |
| `MEASure:Volt?` | Gets the value | `MEAS:V?` | `10` |
| `*OPC?` | Waits for command completion and returns the status | `*OPC?` | `1` |
| `SYSTem:ERRor?` | Returns the error message | `SYST:ERR?` | `invalid command: IDN?` <br>(after sending `IDN?` instead of `*IDN?`) |

The SlowPy SCPI server binds SCPI commands to handlers using decorators.
As with `set_V(value:float)` in this example, if the arguments of a handler function have type annotations, type checking and type conversion are performed on calls.
SCPI command concatenation, etc. is processed before the handlers are called.
Default handler implementations are provided for some standard commands, such as `*OPC?` and `SYSTem:ERRor?`.

Once the code is tested, make it start automatically on PC boot with your preferred method (systemd, `/etc/rc.local`, Docker, etc.).
Some methods are described in [Related Tools](RelatedTools.html).

If a SlowPy control node for the device already exists, the node can be mapped directly to an SCPI interface.
```python
from slowpy.control import ControlSystem, ScpiServer, ScpiAdapter

ControlSystem.import_control_module('DummyDevice')
device = ControlSystem().randomwalk_device()

adapter = ScpiAdapter(idn='RandomWalk')
adapter.bind_nodes([
    # Randomwalk Configuration
    ('CONFIGure:WALK', device.walk().setpoint(limits=(0,None))),
    ('CONFIGure:DECAY', device.decay().setpoint(limits=(0,1))),

    # Common SCPI commands for power supplies and voltmeters
    ('VOLTage', device.ch(0).setpoint()),
    ('MEASure:VOLTage:DC', device.ch(0).readonly()),
])

server = ScpiServer(adapter, port=5025)
server.start()
```

# SlowTask: Binding the GUI and Scripts
A SlowTask is a user Python script placed under the `config` directory of a SlowDash project, with a name like `slowtask-XXX.py`.
From the SlowDash GUI, the script can be started and stopped, functions defined in the script can be called, variables in the script can be displayed, etc.
The SlowPy library is designed to be used in SlowTask scripts, but using it is not mandatory.

There are two ways to write a SlowTask script:

- **With Tasklet**: create an instance of `slowpy.mesh.Tasklet` in the script, and use decorators to explicitly specify functions exposed externally and functions called at start-up, at fixed time intervals, etc. All features of SlowMesh are available.
- **Without Tasklet**: use a plain Python script as is. All functions whose names do not start with an underscore become callable externally, and functions with predefined names such as `_initialize()` and `_loop()` are called at specific timings. Available features are limited.

The method without Tasklet is for cases where an existing script is to be used with the SlowDash Web GUI as is, or where you do not want to write SlowPy code in the script.
When writing a new script, using Tasklet is easier to manage and more capable.

```python
from slowpy.mesh import Tasklet
tasklet = Tasklet()

... (body) ...

# Block to run the script standalone (optional)
if __name__ == '__main__':
    tasklet.run(mesh_url='slowmq://localhost:18881')
```

## Starting and Stopping SlowTasks
### Starting from the SlowDash Server
When a SlowTask script file (e.g., `slowtask-test.py`) is placed under the `config` directory of the project, it is recognized by the SlowDash server and shown in the task management panel (the "SlowTask" section) of the SlowDash home page.
By default, tasks are only "listed" and are not executed until the `start` button is clicked.

By creating an entry in the SlowDash configuration file (`SlowdashProject.yaml`), a task can be configured to start automatically when the server starts.
```yaml
slowdash_project:
  ...

  task:
    name: test
    auto_start: true
    parameters:
      default_ramping_speed: 0.1

  system:
    our_security_is_perfect: false
```

The `task` entry can be a dict of one task, or a list of multiple tasks (`tasks` can be written instead of `task`).
```yaml
  tasks:
    - name: read
      auto_start: true
    - name: store
      auto_start: true
      parameters:
        db_url: sqlite:///SlowStore.db
        table: slowdata
```

| Parameter | Description | Default |
|---|---|---|
| `name` | Task name | (required) |
| `auto_start` | Whether to start the task automatically when the server starts (the old name `auto_load` can also be used) | `false` |
| `parameters` | Parameters passed to the script | none |
| `file_path` | Path of the script file | `config/slowtask-{name}.py` |
| `command` | Command to start the task | `slowdash-task {file_path} --name={name}` |

`parameters` is optional; if specified, it is passed to the initialize callback of the SlowTask script (described later). It is also held in the `parameters` property of the Tasklet, so it can be used before `initialize`, such as in decorators.

By changing `command`, a task can be run on another PC using `ssh`, for example.
By writing the same script in multiple entries with different names, the same script can be run multiple times simultaneously.

To use a general-purpose SlowTask included in the SlowDash distribution package, prefix `name` with `@toolbox/`.
For details, see the [Toolbox chapter](Toolbox_JP.html) (in Japanese).

Setting `our_security_is_perfect` in `system` to `true` allows Python scripts to be edited on the SlowDash web page.
This is convenient, but think carefully about what it means.
A Python script can do anything, such as `system("rm -rf *")`.
Use this feature only if access is strictly controlled.

### Operating Tasks from the SlowDash Server
The following SlowTask operations can be performed from the SlowDash task management panel:

- **Start**: starts the SlowTask as a child process. The start command can be specified with `command` in the `SlowdashProject.yaml` file; the default is local execution with the `slowdash-task` command.
- **Stop**: requests the task to stop via SlowMesh. The Tasklet stop procedure is performed, and the finalize callbacks are called.
- **Kill**: if the task was started by the server as a child process, sends a KILL signal to the child process.
- **Purge**: removes a task that no longer responds from SlowMesh.

SlowTask processes started from the SlowDash server terminate automatically when the SlowDash server terminates.
(SlowTask processes terminate automatically even if the server crashes or is forcibly killed.)

When the script is modified, stopping the task and starting it again loads the new script.

### Running Independently of the Server
To run a SlowTask as a process independent of the SlowDash server, usually the `slowdash-task` command is used.
The `--mesh` option specifies the SlowMesh endpoint (usually the address of the SlowDash server).
Task parameters can also be passed by giving a JSON string to the `--parameters` option.
In this case, enclose the entire JSON string in single quotes so that it is not misinterpreted by the shell.
```console
$ cd PATH/TO/PROJECT
$ slowdash-task config/slowtask-mytask.py --mesh=slowmq://localhost:18881 --parameters='{"p1":10,"p2":20}'
```

If the script has `if __name__ == '__main__': tasklet.run(...)`, it can also be run as a normal Python script.
In this case, however, task parameters cannot be passed.
```console
$ slowdash-activate-venv
$ python config/slowtask-mytask.py
```

SlowTask processes started independently can also be stopped (Stop) from the SlowDash server.
However, they cannot be forcibly terminated (Kill) from the server.
SlowTask processes started independently keep running even if the SlowDash server stops, and automatically reconnect the next time the SlowDash server starts.
As long as the task can access SlowMesh, the task process may run on another PC or in another container.

### Task Name
Each SlowTask has a name (task name), which is used for function calls from the browser, etc., and for data channel names, etc.
The task name is specified by one of the following:

- The file name of the task script, with the leading `slowtask-` removed (default)
- The `name` parameter of the `task` entry in `SlowdashProject.yaml`
- The `--name` parameter of the `slowdash-task` command
- The `name` argument of `Tasklet.run()`

Task names cannot contain characters other than alphanumerics and `_`.
If such characters are included, they are replaced with `_`.
For example, the task name of `slowtask-my-device.py` will be `my_device`.

## Exporting Functions
User functions in a SlowTask script can be called externally, including from the Web GUI.

### With Tasklet
If a SlowTask script uses Tasklet, functions called from the Web GUI, etc. must be explicitly specified with the `@tasklet.mesh.export()` decorator.
This makes it clear which functions are called externally, even when the script becomes long.

```python
from slowpy.mesh import Tasklet
tasklet = Tasklet()

@tasklet.mesh.export()
async def set_V(ch:int, V0:float, ramping:float):
    ...
```
The function can be either a normal function or an async function.
To export a function under a different name, specify `name` as a keyword argument, as in `@tasklet.mesh.export(name='set_voltage')`.

### Without Tasklet
If a script does not use Tasklet, all functions whose names do not start with an underscore (`_`) are implicitly exported.
(Only the functions defined in the script are exported; imported functions are not.)

```python
def set_V(ch:int, V0:float, ramping:float):
    ...
```

### Execution Time of Exported Functions
As a SlowTask runs entirely concurrently in single-threaded asynchronous processing, using `time.sleep()` in the script freezes everything.
The intended way is to write loops using `@tasklet.loop(interval)` etc. (described later), so that there is no explicit sleep in the script.
If you really need to sleep, use `await asyncio.sleep()` or `await ctrl.aio_sleep()`.

Also, **make exported functions finish immediately; as a guideline, return within 1 second at most**.
The caller times out in 5 seconds by default.
For time-consuming processing, consider the following methods:

- Set the processing request in a variable or put it into an `asyncio.Queue`, and have a `@tasklet.loop()` callback check it and start the processing
- Run it as a separate task with `asyncio.create_task()`
- Use SlowPy nodes that have threads or async tasks, such as ramping and PID

The status and results of the processing are expected to be sent to the browser by streaming, etc., or written to logs.

## Calling Functions from the Web GUI
Exported functions can be called from the SlowDash GUI in several ways.
In the following, the script file name is assumed to be `slowtask-test.py` (task name `test`).

### HTML Form Panel
In a SlowPlot HTML form panel, clicking a `<button>` (or `<input type="submit">`) whose `name` attribute has a task name and a function name calls that function:
```html
<form>
  <button name="test.destroy_apparatus()">Finish</button>
</form>
```
Here, the parentheses at the end of the button name indicate that this button is bound to a SlowTask function.

The first part (`test.` in this example) is the task name, which by default is the script file name with the leading `slowtask-` removed.
(If the task name contains `-`, it is replaced with `_`.)

HTML files are placed in the `config` directory of the project, with names like `html-XXX.html`.
As described later, HTML contents can also be generated in a SlowTask script.

#### Passing Parameters
SlowTask functions can take arguments:
```python
def set_V0(voltage:float, ramping:float):
    #... do your work here
```
The argument values are taken from the values of the `<input>` elements of the form:
```html
<form>
  Voltage: <input type="number" name="voltage" value="0"><br>
  Ramping: <input type="number" name="ramping" value="1"><br>
  <button name="test.set_V0()">Set</button>
</form>
```
The `name` attribute of an `<input>` corresponds to the argument name of the function.
Of the `<input>` elements in the form, only those for the arguments the function takes are passed.

If the SlowTask function has type annotations as in the example above, the argument values are converted to the specified types.
If a value cannot be converted to the specified type, an error is returned to the browser, and the SlowTask function is not called.
The value of a checkbox (`<input type="checkbox">`) can be passed to a `bool` argument.

Multiple buttons can be placed in a single form:
```html
<form>
  Ramping: <input type="number" name="ramping" value="1" style="width:5em">/sec
  <p>
  V0: <input type="number" name="V0" value="0"><button name="test.set_V0()">Set</button><br>
  V1: <input type="number" name="V1" value="0"><button name="test.set_V1()">Set</button><br>
  V2: <input type="number" name="V2" value="0"><button name="test.set_V2()">Set</button><br>
  V3: <input type="number" name="V3" value="0"><button name="test.set_V3()">Set</button><br>
  <p>
  <button name="test.set_all()">Set All</button>
  <button name="test.stop()">Stop Ramping</button><br>
</form>
```
```python
def set_V0(V0:float, ramping:float):
    ...

def set_V1(V1:float, ramping:float):
    ...
```
Web form input values are bound to the function arguments by name (`<input name="V0">` is bound to the argument `V0`).

Instead of passing function arguments from `<input>`, they can also be written directly in the `<button>` name.

```html
<form>
  Ramping: <input type="number" name="ramping" value="1" style="width:5em">/sec
  <p>
  V0: <input type="number" name="V0" value="0"><button name="test.set_V(ch=0)">Set</button><br>
  V1: <input type="number" name="V1" value="0"><button name="test.set_V(ch=1)">Set</button><br>
  V2: <input type="number" name="V2" value="0"><button name="test.set_V(ch=2)">Set</button><br>
  V3: <input type="number" name="V3" value="0"><button name="test.set_V(ch=3)">Set</button><br>
  <p>
  <button name="test.set_all()">Set All</button>
  <button name="test.stop()">Stop Ramping</button><br>
</form>
```
```python
def set_V(ch:int, V0:float, ramping:float):
    ...
```

(Execution controls used in previous versions, such as `reentrant` and `async`, have been moved to the Python script side (TODO). The button-name modifiers are no longer needed; if specified, a warning is shown and they are ignored.)

#### Publishing to PubSub
If the button name is `publish TOPIC_NAME()`, instead of calling a function, the form input values are published to the specified SlowMesh topic.
This is used to notify all tasks that need it of an event such as "start", rather than calling a function of a specific task (see the SlowMesh section).
```html
<form>
  <button name="publish mydaq.control.start()">Start</button>
  <button name="publish mydaq.control.stop()">Stop</button>
</form>
```
The published data is a dict combining the arguments in the parentheses and the name-value pairs of the form's `<input>` elements.

#### Form Synchronization
If a `<form>` is given a name, its values are sent to the server on every change of an `<input>`, and the form input values are synchronized across multiple browsers (even before a button is pressed).
Also, the form values are saved to a file in the project directory (`registry-pubsub-form.json`), and the previous form values are automatically restored when the server is stopped and restarted.
```html
<form name="voltage_control">
  Ramping: <input type="number" name="ramping" value="1" style="width:5em">/sec
...
</form>
```

The values of named forms can also be read and written from SlowTask scripts (see "Reading and Writing Form Values" below).

#### Enabling / Disabling Buttons by Data
By specifying the `sd-enabled` attribute on an `<input>`, buttons, etc. can be enabled or disabled according to data values.
Using values streamed or exported from a SlowTask (described later), it is possible, for example, to disable the Start button while running, according to the task status.
```html
<form name="run_control">
  <input type="submit" name="test.start()" value="Start" sd-enabled="run_status['running']->invert()">
  <input type="submit" name="test.stop()" value="Stop" sd-enabled="run_status['running']">
</form>
```
The value specified in `sd-enabled` must be a boolean. For value conversion, see the [Data Transform chapter](DataTransform.html).

### Canvas Panel
In a canvas panel, a button to call a task can be placed as follows:
```json
{
    ...
    "items": [
        {
            "type": "button",
            "attr": { "x":400, "y": 630, "width": 130, "label": "Finish Experiment" },
            "action": { "submit": { "name": "test.destroy_apparatus()" } }
        },
        ...
```

For functions that take arguments, a form can be used:
```json
{
    ...
    "items": [
        {
            "type": "valve", 
            "attr": { ... },
            "metric": { "channel": "sccm.GasInlet", ... },
            "action": { "form": "FlowControl" }
        },
        ...
    ],
    "forms": {
        "FlowControl": {
            "title": "Injection Flow",
            "inputs": [
                { "name": "flow", "label": "Set-point (sccm)", "type": "number", "initial": 15, "step": 0.1 }
            ],
            "buttons": [
                { "name": "ATDS.set_flow()", "label": "Apply Set-point" },
                { "name": "ATDS.stop_flow()", "label": "Close Valve" }
            ]
        }
    }
    ...
```

For details, see the [UI Panels chapter](Panels.html).

### Calling from Other SlowTasks and Programs
Exported functions can also be called from other SlowTasks via SlowMesh remote procedure calls (RPC).
```python
return_value = await tasklet.mesh.aio_call('test.set_V', ch=0, V0=10, ramping=1)
```
They can also be called from programs other than browsers, using the HTTP API (POST to `api/control`).

## Lifespan Callbacks
### With Tasklet
With the decorators provided by tasklet, functions in a SlowTask can be called at specific timings or at fixed time intervals.
The called functions can be either normal functions or async functions. (However, do not use `time.sleep()` in the functions.)

The same decorator can be used multiple times.
In particular, by making multiple small `@tasklet.loop(interval)` functions, one for each processing, there is no need to write loops yourself in the script, avoiding the complexity of sleeping, termination handling, etc.

- `@tasklet.initialize()`: called when the script starts
- `@tasklet.finalize()`: called when the script ends
- `@tasklet.once(delay:float=0)`: called once, the specified number of seconds after initialize
- `@tasklet.schedule(time:str, use_utc:bool=False)`: called repeatedly at the specified time
- `@tasklet.loop(interval:float, ticks=None)`: called repeatedly at the specified interval in seconds

#### Initialization and Finalization
If an `@tasklet.initialize()` function takes one argument, the task parameters specified with `parameters` in `SlowdashProject.yaml` (or `--parameters` of the `slowdash-task` command) are passed as a dict.
```python
@tasklet.initialize()
async def initialize(parameters:dict):
    db_url = parameters.get('db_url', 'sqlite:///SlowStore.db')
    ...

@tasklet.finalize()
async def finalize():
    datastore.close()
```
Task parameters can also be obtained from `tasklet.parameters`.

Other callbacks, such as loop and once, start after all the initialize callbacks have finished.
Finalize callbacks are called after a task stop request (Stop from the browser, Ctrl-c, etc.), once the other callbacks have stopped.

#### Scheduled Execution
With the `@tasklet.schedule(time)` decorator, a user function can be called repeatedly at specified times.

```python
@tasklet.schedule("08:00")
def do_this_every_morning():
   # executed every morning at 8:00
   pass
```

The `time` argument is specified in the `HH:MM` format. The wildcard `*` can be used for `HH` and `MM`, and multiple time settings can be listed separated by `,`. To keep the period from changing at daylight saving time transitions, set `use_utc` to `True` and specify the time in UTC.

Examples:

- `@tasklet.schedule("08:00")`: every morning at 8:00
- `@tasklet.schedule("00:00,08:00,16:00")`: three times a day
- `@tasklet.schedule("*:00")`: every hour on the hour
- `@tasklet.schedule("*:*")`: every minute
- `@tasklet.schedule("*:00,*:20,*:40")`: three times an hour
- `@tasklet.schedule("08:00", use_utc=True)`: every day at 8:00 UTC

Unless `use_utc` is specified, times are in local time, but note that when running inside a container such as Docker, the local time is often UTC.

#### User Loop
With the `@tasklet.loop(interval)` decorator, a user function can be called repeatedly at a specified period.

```python
@tasklet.loop(interval=1)
async def my_work():   # this function is called every 1 second (the value of interval)
    #... do my work
    pass
```

Furthermore, if `ticks` is specified in `@tasklet.loop` and a `tick` argument is added to the user function, the value of `tick` becomes True every `ticks` times (the argument name of the user function is arbitrary).
```python
@tasklet.loop(interval=1, ticks=10)
async def my_work(tick):
    # read data every second, and send all the data to the stream
    data = await HV.ch(0).aio_get()
    packet = DataPacket(data, tag='HV.ch00')
    
    await tasklet.mesh.aio_publish(packet.to('data.stream'))
    
    # record into the database once every 10 times
    if tick:
        await tasklet.mesh.aio_publish(packet.to('data.store'))
```

Multiple tick periods can also be specified.
```python
@tasklet.loop(interval=1, ticks={"transient_store":10, "store":60})
async def my_work(tick):
    # read data every second, and send all the data to the stream
    data = await HV.ch(0).aio_get()
    packet = DataPacket(data, tag='HV.ch00')
    
    await tasklet.mesh.aio_publish(packet.to('data.stream'))
    
    # record into the transient database (short-term, high-density) once every 10 times
    if tick.transient_store:
        await tasklet.mesh.aio_publish(packet.to('data.transient_store'))
        
    # record into the persistent database once every 60 times
    if tick.store:
        await tasklet.mesh.aio_publish(packet.to('data.store'))
```
(For `DataPacket` and `aio_publish()`, see the SlowMesh section below.)

Again, do not use `time.sleep()` in user functions (`await ctrl.aio_sleep()` is OK).
By using `@tasklet.loop()`, most sleeps should be eliminated.

### Without Tasklet
If a script does not use Tasklet, the following functions, if defined, are called at specific timings.

| Function | Description | Tasklet Equivalent |
|---|---|---|
| `_initialize(params)` | Called once when the script is loaded. The value of `params` is given by the SlowDash configuration. | `@tasklet.initialize()` |
| `_run()` | Called once after `_initialize()`. | `@tasklet.once()` |
| `_loop()` | Called repeatedly after `_initialize()`, until the user stops the system. | `@tasklet.loop(interval=0)` |
| `_finalize()` | Called once after `_run()` or `_loop()`. | `@tasklet.finalize()` |
| `_get_html()` | Returns HTML content (described later). | `@tasklet.content('config/html-{TASK_NAME}.html')` |
| `_get_layout()` | Returns a SlowPlot layout (described later). | `@tasklet.content('config/slowplot-{TASK_NAME}.json')` |

Note that, unlike when using Tasklet, the `_loop()` function is called repeatedly and immediately, without sleeping.
Therefore, `_loop()` needs to sleep to adjust the period.
The called functions can be either normal functions or async functions, but `_loop()` needs to be async, so that `await ctrl.aio_sleep()` etc. can be used instead of `time.sleep()`.
```python
from slowpy.control import control_system as ctrl

async def _loop():
    ...
    await ctrl.aio_sleep(1)
```
If `_loop()` is a normal function, a small delay (0.1 seconds) is inserted between `_loop()` calls to avoid starvation, and a warning is shown.

`_run()` also needs to be async in the same way.
If `_run()` runs for a long time, monitor `ctrl.is_stop_requested()` and terminate when a stop is requested.
(`_halt()`, which was used in previous versions, is no longer called.)
```python
async def _run():
    while not ctrl.is_stop_requested():
        ...
        await ctrl.aio_sleep(1)
```

A normal-function `_loop()` like the following, which was common in scripts of previous versions, also works (with a warning).
Note, however, that the entire task stops during `ctrl.sleep()`, delaying responses to function calls from the browser, etc.
```python
def _loop():
    ...
    ctrl.sleep(1)
```

## Sending Data to the Browser
In addition to recording data into a database and reading it from the browser, there are the following ways to send data from a SlowTask to the browser:

- **Streaming**: sends values out from the SlowTask and displays them in real time on the browser (push)
- **Exporting variables**: exposes variables in the SlowTask, and returns the current values on requests from the browser (pull)
- **Dynamic content generation**: generates HTML and layout contents in the SlowTask

In all cases, only the "current" values are available. If history is needed, record the data into a database.

### Streaming
Using the `aio_stream(name:str, value)` method (or `stream(name:str, value)`) of ControlSystem, values can be sent from a SlowTask script to the browser for live updates.
```python
from slowpy.mesh import Tasklet
tasklet = Tasklet()

from slowpy.control import control_system as ctrl
V0 = ctrl.ethernet(host, port).scpi().command("V")

@tasklet.loop(interval=1.0)
async def loop():
    await ctrl.aio_stream('V0', await V0.aio_get())   # pushing to consumers
```
The types of values that can be streamed include numbers, strings, dicts, Python dataclasses, SlowPy control nodes, and SlowPy analysis objects (histograms, etc.).
Numbers and strings are handled as scalar data, and dataclasses and dicts as Tree-type data.
The sent values are shown in the Data Channels of the browser as data of the `current` type, and can be added to panels just like normal data.

`stream()` can also be used from non-async functions, but it must be running as a SlowTask (the Tasklet event loop must be running).
Internally, the values are published to the SlowMesh topic `data.stream.{name}`.

### Exporting Variables
With the `expose(name:str, obj)` method of ControlSystem, variables in a SlowTask can be exposed.
Exposed variables can be accessed from the browser as data channels named `{TASK_NAME}.{name}`, just like data in a database (it looks as if a single data point with the timestamp of "now" is stored).
While streaming is a push from the SlowTask, exporting is a pull interface that returns values on requests from the browser. It is suitable for "getting the latest value when needed".

```python
from dataclasses import dataclass

@dataclass
class RunStatus:
    run_number: int = 1
    running: bool = False
run_status = RunStatus()

@tasklet.initialize()
async def initialize():
    ctrl.expose('status', run_status)    # if the task name is run_control, the channel name is run_control.status
```
Things that can be exported include control nodes, SlowPy analysis objects, dicts, dataclasses, etc.
Call `expose()` after the Tasklet has started (e.g., in an initialize callback).

Control nodes can also be exported directly with `tasklet.mesh.export(name, node)`.
Here is an example of creating and exporting a node that returns disk usage.
```python
import shutil
from slowpy.control import ControlNode

class DiskUsageNode(ControlNode):
    async def aio_get(self):
        total, used, free = tuple((int(x*1e-8)/10.0) for x in shutil.disk_usage('.'))
        return { 'tree': { 'total_GB': total, 'used_GB': used, 'free_GB': free } }

tasklet.mesh.export('disk_usage', DiskUsageNode())
```
Restrict operations on nodes exposed externally with `readonly()` etc. as necessary.

### Reading and Writing Form Values
Input values of named HTML forms can be read and written from a SlowTask, using the `form(name)` node of ControlSystem.
For example, the values last entered on the browser can be used as initial values when the task starts, or values determined by the task can be shown in the browser form.
```python
@tasklet.initialize()
async def initialize():
    # get the current input values of the browser form "pid_setup" as a dict
    form = await ctrl.form('pid_setup').aio_get()
    Kp = form.get('Kp', 1)
    ...

@tasklet.mesh.export()
async def stop():
    ...
    # change the displayed value of the "run_number" input of the form "run_control"
    await ctrl.form('run_control').element('run_number').aio_set(run_status.run_number)
```
Multiple input values can also be set at once with `ctrl.form(name).aio_set(dict)`.

### Dynamic Content Generation
With the `@tasklet.content(name)` decorator, the contents of files that are normally placed under `config` of a SlowDash project can be generated dynamically.
This makes it possible to put a task script and the HTML form to control it into a single file, making it easier to keep them consistent.
```python
@tasklet.content('config/html-test.html')
def html():
    return '''
      <form name="test">
        Voltage: <input type="number" name="voltage" value="0">
        <button name="test.set_V0()">Set</button>
      </form>
    '''
```
From the browser, it looks as if the HTML file `html-test.html` exists in `config`.

If `On Update: Reload HTML` is checked in the HTML panel, this function is called on every data update, so HTML pages containing data can be generated dynamically.
Here is an example of displaying disk usage formatted in a table.
```python
import shutil

@tasklet.content('config/html-disk_usage.html')
def html_disk_usage():
    total, used, free = tuple((int(x*1e-8)/10.0) for x in shutil.disk_usage('.'))
    return f'''
    <table>
      <tr><td>Total</td><td>{total} GB</td></tr>
      <tr><td>Used</td><td>{used} GB</td></tr>
      <tr><td>Free</td><td>{free} GB</td></tr>
    </table>    
    '''
```

`config/slowplot-XXX.json` can be generated in the same way, so together with an HTML form, a SlowTask can provide a complete layout to use it.
As content generation functions are ordinary Python functions, template engines such as Jinja can also be used with them.

## Matplotlib Integration
Matplotlib Figures can be streamed directly to a SlowDash layout without changing the script.
```python
import matplotlib.pyplot as plt

async def _loop():
    fig, axes = plt.subplots(2, 2)
    #... draw plots in the usual way

    fig.show()   # this is overriden by SlowDash
    
    await asyncio.sleep(1)
```
SlowDash overrides `Figure.show()` to extract the layout, and reads the values of histograms and graphs from the drawn figures.
It then dynamically generates a `slowplot-XXX.json` with the same layout, and sends the data out to SlowDash streaming.
Instead of `Figure.show()` as in the example, using `pyplot.show()` or `Figure.savefig(name)` also streams to SlowDash.
(With `savefig()`, the normal file saving is also performed.)
The name of the generated layout is the task name for `Figure.show()` and `Figure.savefig()`, and `{TASK_NAME}.fig{NUMBER}` for `pyplot.show()`.

When running as a SlowTask, the Matplotlib GUI is disabled (the `Agg` backend is used).

Other examples are in `ExampleProjects/Streaming/Matplotlib`.

# SlowMesh
Multiple SlowTask scripts can be deployed over a network and work cooperatively, communicating over SlowMesh.
SlowMesh is the communication infrastructure for message exchange between the SlowDash server and SlowTasks, and provides the following communication features:

- **PubSub**: exchange of messages with topic names (Publish / Subscribe)
- **Remote Procedure Call (RPC)**: calling functions exported by other tasks
- **Registry (Key-Value Store)**: a store of named values shared among tasks

<img src="fig/SlowMeshConcept.png" width="40%">

In PubSub, the sender publishes messages without knowing the receivers, and receivers subscribe to the topics they need without knowing the senders.
This is very different from remote procedure calls, where communication is done with knowledge of the counterpart's behavior and interface, and greatly reduces the interdependency between components.
SlowDash actively uses PubSub, and performs distributed processing with the model of "when you read data, throw it to the mesh (assuming someone you don't know will process it)", "receive related topics by yourself", "fulfill your own responsibility for the received data", and "when you generate processing results, throw them to the mesh".
For example, dividing functions into "a task that publishes data to SlowMesh when it reads it", "a task that receives data and records it into a database", and "a task that receives data, analyzes it, and publishes the results" makes it possible to develop, test, and restart each task independently.

## Basic Usage
A SlowTask holds a connected SlowMesh through the Tasklet, and each feature can be used from `tasklet.mesh`.

```python
from slowpy.mesh import Tasklet, DataPacket
tasklet = Tasklet()

# publish data to the data.store topic (the arguments of DataPacket are the same as DataStore.append())
@tasklet.loop(interval=1)
async def read_data():
    volt = float(await device.command('MEAS:VOLT:DC').aio_get())
    await tasklet.mesh.aio_publish(DataPacket(volt, tag='volt').to('data.store'))

# subscribe to topics under data.store, and record into the database
@tasklet.mesh.on('data.store.>')
async def store(data:DataPacket):
    for channel, value in data.values.items():
        datastore.append(value, tag=channel, timestamp=data.timestamp)

# call a function of another task
@tasklet.mesh.export()
async def start():
    await tasklet.mesh.aio_call('histogram.clear')

# store and get values in the registry
@tasklet.initialize()
async def initialize():
    run_number = await tasklet.mesh.registry.aio_get('setup.run.number', 0)
    await tasklet.mesh.registry.aio_set('setup.run.number', run_number + 1)
```

Currently, values that can be sent and received over SlowMesh (published data, RPC arguments and return values, registry values) are limited to those that can be serialized to JSON.

## Connecting to SlowMesh
### Endpoint
The connection to SlowMesh is made automatically by the Tasklet. The endpoint URL is determined as follows:

- When started from the SlowDash server: specified by the server with the `--mesh` option of the `slowdash-task` command
- When started independently with the `slowdash-task` command: specified with the `--mesh` option
- When the script is run directly: specified with `tasklet.run(mesh_url=...)`

If no endpoint URL is given, a local PubSub closed within the process is used.
In this case, messages published by the task itself can be subscribed to by itself, but communication with other tasks and use of the registry are not possible.
This can be used for checking the behavior of a script standalone, etc.

### Messaging Backbone
SlowMesh uses a messaging backbone as the underlying communication layer.
By default, SlowMQ, which is built into the SlowDash server, is used, so it can be used as is without any configuration.
SlowMQ is implemented with WebSockets over HTTP(S), and can be accessed directly at the URL (port) of the SlowDash server.

Instead of SlowMQ, widely used external messaging systems such as NATS, MQTT, Redis, and RabbitMQ can also be used.
In this case, specify the endpoint with the `mesh` entry in `SlowdashProject.yaml`. The same URL is also passed to the tasks started from the server.
```yaml
slowdash_project:
  ...
  mesh:
    url: nats://localhost
```

| Backbone | URL Format | Broker | Notes |
|---|---|---|---|
| SlowMQ | `slowmq://HOST:PORT` (HTTP) or `slowmqs://HOST:PORT` (HTTPS) | Not needed (built into SlowDash) | Default. Accessible across firewalls |
| NATS | `nats://HOST` | Separate NATS server required | |
| MQTT | `mqtt://HOST` | Separate MQTT broker (eclipse-mosquitto, etc.) required | |
| RabbitMQ | `rabbitmq://USER:PASS@HOST/EXCHANGE` | Separate RabbitMQ server required | |
| Redis-PubSub | `redis://HOST/DB` | Separate Redis server required | Limitations on topic filters |

If credentials are required, insert `USER:PASS@` right before `HOST`.

For QoS settings (at-most-once / at-least-once / exactly-once) etc., the backbone defaults are basically used.
The intended operation is to switch the backbone as the system evolves (start with SlowMQ, and migrate to NATS when performance or features become insufficient, etc.).
Switching the backbone does not require changing user scripts.

To connect to an external messaging system separately from the main SlowMesh, an additional Mesh object can be created with `tasklet.external_mesh(url)`.
It is started and stopped together with the main Mesh, and can be used with the same interface, such as `on()` and `aio_publish()`.

## PubSub
### Publish
```python
# publish with a topic name and a value
await tasklet.mesh.aio_publish('mydaq.control.start', {'run_number': 10})

# publish a MeshPacket (the topic name is determined by the MeshPacket)
await tasklet.mesh.aio_publish(DataPacket(volt, tag='volt').to('data.store'))
```
`aio_publish()` is an async function. From non-async functions, use `publish()` instead (the arguments are the same).
Even when using `publish()`, it must be running as a SlowTask (the Tasklet event loop must be running).

Headers can be attached to a message by passing a dict to the `headers` argument.

### Subscribe
The `@tasklet.mesh.on(topic)` decorator specifies a function to be called when a message of the specified topic is received.
The function can be either a normal function or an async function.
```python
@tasklet.mesh.on('mydaq.control.start')
async def handle_start(data):
    run_number = data.get('run_number')
    ...
```
What is passed depends on the number of arguments and the type annotations of the function.

| Function Form | What Is Passed |
|---|---|
| `def handler()` | Nothing (when you only want to know that a message was received) |
| `def handler(data)` | Message body |
| `def handler(packet:DataPacket)` | Message converted to a MeshPacket (described later) |
| `def handler(headers, data)` | Headers and message body. The received topic name is `headers['topic']` |

When receiving multiple topics with a topic filter, use the last form if you need to know the actual topic name.

To add a subscription dynamically during execution, use `await tasklet.mesh.aio_subscribe(topic, handler)`.

### Topic Names and Topic Filters
Topic names can have a hierarchical structure separated by `.`, as in `data.store.HV.ch01`.
The following topic filters can be used in subscriptions (same as NATS):

- `*` matches any single level
- `>` matches any number of trailing levels (can only be used as the last character)

For example, `data.store.>` matches all topics under `data.store`, and `data.*.HV.ch01` matches both `data.store.HV.ch01` and `data.stream.HV.ch01`.

When a backbone other than SlowMQ or NATS is used, these characters are replaced with the corresponding characters of that backbone (`/`, `+`, `#`, etc. for MQTT).
Therefore, including characters such as `/`, `#`, `+`, and `:` in topic names causes problems with some backbones. Avoid using these characters.
Also, as Redis does not have a strict hierarchical structure, the filter behavior may be approximate.

### Topic Name Allocation
Topic names are reserved throughout SlowDash, but the following can be used freely by users:

- Names starting with an uppercase letter (`KamLAND.control.start`, etc.)
- Names starting with `my` (`my.>`, `mydaq.>`, etc.)
- Names starting with `test` (`test.>`, `testdaq.>`, etc.)
- `setup.>`
- `user.>`

The main topics used by SlowDash are:

| Topic | Content | MeshPacket |
|---|---|---|
| `data.store.{channel}` | Data to be recorded (usually saved into a database by a recording task) | `DataPacket` |
| `data.stream.{channel}` | Data for display (not recorded) | `DataPacket` |
| `form.{form_name}.{element_name}` | Input values of named HTML forms | `FormPacket` |
| `log.{level}.{logger}` | Log messages | |
| `sd.>` | Internal use by SlowDash (task management, RPC, etc.) | |

For data flowing on topics starting with `data.`, the SlowDash server keeps the latest value of each channel, which can be displayed on the browser as `current` data.
The `ctrl.stream()` described above publishes data to the `data.stream.{name}` topic.

### MeshPacket
Some topics used by SlowDash have a defined message schema (data structure).
Using MeshPackets, user scripts do not depend on the details of the schema, and the effort of constructing and decoding messages is saved.

| MeshPacket | Target Topics | Constructor |
|---|---|---|
| `DataPacket` | `data.*.>` | `DataPacket(values, *, tag=None, timestamp=None)` |
| `FormPacket` | `form.*.>` | `FormPacket(form, element, value)` |

#### DataPacket
The constructor arguments of `DataPacket` are the same as `DataStore.append()`.
That is, recording directly into a data store and publishing to SlowMesh are written almost the same way.
```python
from slowpy.mesh import DataPacket

temp0 = thermometer.ch(0).get()
await tasklet.mesh.aio_publish(DataPacket(temp0, tag='temp0').to('data.store'))
```
The topic to publish to is `data.store.{channel}` by default, and the `data.store` part can be changed with `to(topic_prefix)` (`to('data.stream')`, etc.).
In addition to numbers, SlowPy analysis objects such as histograms, and time-series data such as `timeseries()` of a Trend, can also be sent.

On the receiving side, if the argument of the handler function has a `DataPacket` type annotation, the received message is converted to a DataPacket and passed.
```python
@tasklet.mesh.on('data.>')
async def handle_data(data:DataPacket):
    t = data.timestamp
    for channel, value in data.values.items():
        ...
```
The `values` of a received DataPacket is a dict with channel names as keys and values as values.

#### FormPacket
When an input value of a named HTML form is changed, a message is published to the `form.{form_name}.{element_name}` topic.
By subscribing to it, changes of input values can be responded to immediately, even before a button is pressed.
```python
from slowpy.mesh import FormPacket

@tasklet.mesh.on('form.pid_setup.>')
async def handle_form(packet:FormPacket):
    print(packet.form, packet.element, packet.value)
```
Conversely, publishing a `FormPacket` changes the form values displayed on the browser.
Usually, using the `ctrl.form(name)` node described above is easier.

### PubSub Last-Value Cache
The SlowDash server subscribes to all PubSub topics, and keeps the latest message of each topic in the registry at `pubsub.{TOPIC_NAME}`.
This allows tasks started later to obtain status information, etc. published before.
```python
@tasklet.initialize()
async def initialize():
    # the last published mydaq.status message
    status = await tasklet.mesh.registry.aio_get('pubsub.mydaq.status')
```

## Remote Procedure Call (RPC)
RPC is a mechanism for calling functions exported by a SlowTask by name from other SlowTasks.
Function calls from the browser also use RPC internally.

### Callee Side
For exporting functions, see the "Exporting Functions" section above.
```python
@tasklet.mesh.export()
async def chat(line, *, sender=None):
    print(f'You ("{sender}") sent me "{line}".')
    return str(datetime.datetime.now())
```
The return value must be a value that can be serialized to JSON.
Also, as described above, exported functions should return within about 1 second as a guideline.

### Caller Side
```python
return_value = await tasklet.mesh.aio_call('chat_task.chat', line, sender='me')
```

- The first argument is `TASK_NAME.FUNCTION_NAME`, and the subsequent arguments are passed as is to the remote function.
- Only values that can be serialized to JSON can be passed as arguments.
- If an exception occurs in the callee, or if there is no response before the timeout (e.g., the callee task is not running), an exception is raised.
- The default timeout is 5 seconds.

To specify a timeout per call, use `aio_call_many()`.
```python
replies = await tasklet.mesh.aio_call_many('chat_task.chat', [line], {'sender': 'me'}, expected_replies=1, timeout=10, raise_on_timeout=True)
```
`aio_call_many()` returns a list of replies. Each reply is a dict with fields like the following:
```python
{ 'status': 'ok', 'message': 'ok', 'return_value': result }
```
In addition to `ok`, `status` can be `error` or `cancelled`; in case of an error, `message` contains the error message.

### Remote Access to Control Nodes
Control nodes exported with `tasklet.mesh.export(name, node)` can be accessed from other tasks using `remote_node()`, in the same way as local nodes.

Callee side (task name `device`):
```python
from slowpy.control import control_system as ctrl

V0 = ctrl.ethernet('192.168.1.43', 5025).scpi(append_opc=True).command('VOLT')
tasklet.mesh.export('V0', V0.setpoint(limits=(0, 100)))
```

Caller side:
```python
V0 = tasklet.mesh.remote_node('device.V0')

await V0.aio_set(10)
print(await V0.aio_get())
```
Remote nodes only have the async versions, `aio_set()` and `aio_get()`.

## Registry (Key-Value Store)
The Registry is a store of named values shared by multiple SlowTasks.
It is intended for sharing states, settings, processing requests, etc. among tasks.
As the registry service runs inside the SlowDash server, a connection to the SlowDash server is required to use it.

### Basic Operations
The registry is accessed via `tasklet.mesh.registry`.
```python
registry = tasklet.mesh.registry

# set a value
await registry.aio_set('setup.run.number', run_number)

# get a value (the default value is returned if the key does not exist)
run_number = await registry.aio_get('setup.run.number', 0)
```

The Registry has the following methods:

- Write (set): `aio_set(key, value, *, cas_revision:int|None=None) -> int|None`
- Read (get): `aio_get(key:str, default=None, *, with_meta:bool=False)`
- List keys (keys): `aio_keys(prefix:str='', limit:int|None=1000) -> list[str]`
- Delete (delete): `aio_delete(key:str, *, cas_revision:int|None=None) -> bool`

### Keys and Values
**Keys**: Keys have a hierarchical structure separated by `.`.
For the name of each level, use names like identifiers (variable names, etc.) in programming languages such as Python. Specifically, names must consist only of alphanumerics or underscores, and must not start with a digit.

**Values**: Currently, only values that can be serialized to JSON can be used.

**Allocation**: Key names are also reserved throughout SlowDash, but as with topic names, the following can be used freely by users:

- Names starting with an uppercase letter (`KamLAND.>`, etc.)
- Names starting with `my` (`mydaq.>`, etc.)
- Names starting with `test` (`testdaq.>`, etc.)
- `setup.>`
- `user.>`

### Grouping Hierarchies
By appending `>` to the end of a key, the entries under that level can be handled together as a single dict.
```python
await registry.aio_set('user', 'slowuser')
await registry.aio_set('state.run.mode', 'physics')
await registry.aio_set('state.run.number', 123)

print(await registry.aio_keys('state.run'))       # -->  ['state.run.mode', 'state.run.number']
print(await registry.aio_get('state.run.mode'))   # -->  physics
print(await registry.aio_get('state.run.>'))      # -->  {'mode': 'physics', 'number': 123}
print(await registry.aio_get('.>'))               # -->  {'user': 'slowuser', 'state': {'run': {'mode': 'physics', 'number': 123}}}
```

With `aio_set()` as well, appending `>` to the end of the key and passing a dict as the value creates entries under that level with the dict expanded.
That is, the following two behave the same:
```python
doc = {'run': {'mode': 'physics', 'number': 123 }, 'running': True }
await registry.aio_set('state.>', doc)
```
```python
await registry.aio_set('state.run.mode', 'physics')
await registry.aio_set('state.run.number', 123)
await registry.aio_set('state.running', True)
```

Note that this is different from passing a dict as a value without `>`.
The following stores the whole thing as a single dict value in one entry:
```python
await registry.aio_set('state', doc)
```
In both cases, `aio_get('state.>')` returns the same result, but in the latter case, the entry `state.run.number` does not exist, so `aio_get('state.run.number')` returns the default value.
Usually, expanding and storing with `>` causes fewer problems, but for recording dicts containing arrays etc., storing without expansion is necessary.

If a value is recorded at a level, and values are also recorded at levels below it, the value of that level is put in a field named `$value` when retrieved as a group.
(This is because a node having both a value and child nodes cannot be represented in a dict or JSON.)
```python
await registry.aio_set('state.run', 'running')
print(await registry.aio_get('state.run.>'))      # -->  {'mode': 'physics', 'number': 123, '$value': 'running'}
```
To avoid confusion, do not record values at levels that have child nodes. In this example, the problem can be avoided by recording at `state.run.status` etc. instead of `state.run`.

### Compare-And-Set (CAS)
The Registry has a Compare-And-Set (CAS) option to prevent unintentionally overwriting what other tasks have written.

- Each entry is assigned a CAS revision, which counts the number of writes
- `aio_set()` increments the CAS revision and returns the new CAS revision
- If the `cas_revision` option of `aio_set()` is not None, the write fails unless its value matches the stored CAS revision
- Similarly, `aio_delete()` fails to delete unless the CAS revision matches

This avoids unknowingly overwriting a value that someone else has changed after you set it.

If the `with_meta` option of `aio_get()` is set to `True`, metadata including the CAS revision and the write time is returned instead of the value:
```python
{
    "key": KEY,
    "value": VALUE,
    "revision": CAS_REVISION,
    "updated": LAST_WRITE_TIME
}
```

### Persistence
Registry values are normally kept only in the memory of the SlowDash server, and are lost when the server is restarted.
Some entries are saved to a file in the project directory (`registry-{PATH}.json`) on every write, and are automatically loaded the next time the server starts.
Currently, only the input values of named HTML forms (`pubsub.form.>`) are persisted.

### Access from the Browser
Values recorded in the registry can be displayed on the browser, just like data in a database.
Specify `@registry:{KEY}` as the data channel name (for example, `@registry:setup.run.number`, or `@registry:setup.run.>` to display the whole hierarchy as a Tree).

They can also be accessed through the Web API.
```console
$ curl http://localhost:18881/api/registry/value/setup.run.number
```

## Forwarding Standard I/O and Logs
Messages written to the standard output / standard error in a SlowTask, by `print()` etc., are published to SlowMesh and shown in the console of the SlowDash home page.
(They are also written to the local standard output.)
If this forwarding is not needed, use `Tasklet(use_mesh_stdio=False)`.

Messages written to Python's standard `logging` are also forwarded to the SlowMesh topic `log.{LEVEL}.{LOGGER_NAME}`.

## Examples
An example of separating SlowTasks by function (reading, recording, and analysis) using SlowMesh is in the [Quick Tour](QuickTour.html).
