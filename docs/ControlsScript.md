---
title: Controls Script
---

# Overview
SlowDash integrates Python scripts written by users, with features including:

- calling user functions from GUI
- reading and writing variable values from GUI
- streaming data from user script to GUI

SlowDash provides a Python library, slowpy, to provide functions for:

- control and readout from measurement hardware
- interface to external software systems, especially messaging systems
- unified interface for data stores
- basic analysis elements such as histograms and graphs


## Applications
- Send commands and receive data to/from external systems (either software or hardware), including:
  - Another concurrent system (DAQ system, etc.)
    - Through a messaging system, such as Redis, AMQP, Kafka, ZMQ, ...
    - Through HTTP GET/POST, or Socket messages
    - By running a shell command
  - Measurement devices that accept commands
    - SCPI measurement devices with Ethernet interface
    - Anything that can be used from Python
      - Raspberry-Pi GPIO, I2C, SPI, ...
      - USB devices with a vendor library
  - Another SlowDash instance for distributed systems
- Analyze data in real-time, construct histograms, etc., and issue alarms
- Store raw and analyzed values (including histograms) in database systems

## Structure
<img src="fig/ContrlScript-UserTask.png" width="40%">

- Controls are implemented as a user task Python script.
- The user task script is a normal Python script. Scripts are executable independently from the SlowDash server.
- Panels on the SlowDash GUI, built by users, can call functions defined in user task scripts.
- A Python library, `slowpy`, is provided to be imported by the user task scripts, for:
  - Simple unified methods to control external systems
  - Data classes such as histograms, graphs, time-series, etc.
  - Data storage interface to store the data objects, as well as raw data from the external systems

## Simple Examples
#### Reading data from a voltmeter with SCPI commands over Ethernet
```python
from slowpy.control import ControlSystem
ctrl = ControlSystem()

# make a control node for a SCPI command of "MEAS:V0" on a device at 192.168.1.43
V0 = ctrl.ethernet(host='192.168.1.43', port=17674).scpi().command('MEAS:V0')

while True:
  # read a value from the control node, with a SCPI command "MEAS:V?"
  value = V0.get()
  ...
```

#### Writing data to PostgreSQL database (using a default schema)
```python
from slowpy.store import DataStore_PostgreSQL

datastore = DataStore_PostgreSQL('postgresql://postgres:postgres@localhost:5432/SlowTestData', table="SlowData")

while True:
    value = ...
    datastore.append(value, tag="ch00")
```

#### Calling a User Task function from SlowDash GUI Panels
If you have a User Task Script like this:
```python
def set_V0(value):
    V0.set(value)
```
and write a SlowDash HTML panel like this:
```html
<form>
  V0 value: <input name="value">
  <input type="submit" name="test.set_V0()" value="Set">
</form>
```
Then, clicking the `Set` button will call the function `set_V0()` with a parameter from the `value` input field. 

#### Displaying the readout values on the SlowDash panels
For control nodes `V0` and `V1`, defining an `_export()` function in the User Task Script will export these node values, making them available in the SlowDash GUI in the same way as values stored in the database.
```python
device = ctrl.ethernet(host='192.168.1.43', port=17674).scpi()
V0 = device.command('MEAS:V0')
V1 = device.command('MEAS:V1')
def _export():
    return [
        ('V0', V0),
        ('V1', V1)
    ]
```
Only the "current" values are available in this way. If you need historical values, store the values in a database.


## Demonstration Example Project
In `slowdash/ExampleProjects/SlowTask` there is a SlowDash project to demonstrate some of the features described here.
```console
$ cd slowdash/ExampleProjects/SlowTask
$ slowdash --port=18881
```
or
```console
$ cd slowdash/ExampleProjects/SlowTask
$ docker compose up
```


# SlowPy: Controls Library
SlowPy is a Python library (module) that provides functions such as:

- connecting external concurrent systems and/or measurement hardware
- histograms, graphs, etc.
- storing raw values, time-series, and histograms/graphs to the database in a way that SlowDash can easily handle.

The SlowPy library is included in the SlowDash package, under `slowdash/lib/slowpy`. By running `source slowdash/bin/slowdash-bashrc`, as instructed in the Installation section, this path will be included in the environmental variable `PYTHONPATH`, so that users can use the library without modifying their system. It is also possible to install the library in the usual way: you can do `pip install slowdash/lib/slowpy` to install SlowPy into your Python environment. You might want to combine this with `venv` to avoid messing up your Python environment.

## Controls
SlowPy provides a unified interface to connect external software systems and hardware devices; everything will be mapped into a single "ControlTree" where each node has `set()` and `get()` methods. The tree represents the logical structure of the system. For example, a SCPI command of `MEAS:V` to a voltmeter connected via Ethernet would be addressed like `ControlSystem.ethernet(host, port).scpi().command('MEAS:V')`, and `set(value)` on this node will send a SCPI command of `MEAS:V?` to the voltmeter. The `get()` method makes a read access and returns a value.

Plugin modules can dynamically add branches to the control tree. For example, the Redis plugin adds the `redis()` node and several sub-branches for functions provided by Redis, such as hash, JSON, and time-series. Plugins are loaded to a node, not (necessarily) to the root ControlSystem; for example, a plugin that uses Ethernet is loaded to an Ethernet node, creating a sub-branch under the Ethernet node, and the plugin can make use of the functions provided by the Ethernet node such as `send()` (which is `set()` of the node) and `receive()` (which is `get()`).

### Example
Here is an example of using SlowPy Controls. In this example, we use a power supply device that accepts SCPI commands through Ethernet.

```python
from slowpy.control import ControlSystem
ctrl = ControlSystem()

# make a control node for a SCPI command of "MEAS:V0" on a device at 192.168.1.43
V0 = ctrl.ethernet(host='192.168.1.43', port=17674).scpi().command('MEAS:V0', set_format='V0 {};*OPC?')

# write a value to the control node: this will issue a SCPI command "V0 10;*OPC?"
V0.set(10)

while True:
  # read a value from the control node, with a SCPI command "MEAS:V"
  value = V0.get()
  ...
```
A common starting point would be importing `slowpy.control`, and then creating an instance of the `ControlSystem` class.

The `ControlSystem` already includes the `Ethernet` plugin, but if it were not, the plugin loading code would have been:
```python
ctrl.load_control_module('Ethernet')
```
This will search for a file named `control_Ethernet.py` from search directories, load it, and inject the `ethernet()` Python method to the node class that loaded the plugin (which is ControlSystem in this case). The Ethernet plugin already includes sub-branches for SCPI; for specific protocols not already included, a plugin would be loaded onto the Ethernet node.

Each node constructor takes parameters. In this example, the Ethernet node, which sends and receives data to/from the Ethernet, takes the host/IP and port parameters, and a SCPI command node, which is bound to a specific SCPI command, takes the SCPI command parameter with optional `set_format` which overrides the default SCPI command for writing. (The default SCPI commands to be written/read for `.scpi().command(CMD)` are `CMD` and `CMD?`, respectively. Often, write operations should wait for command completion, and SlowPy expects a return value from each command. A technique to do this, regardless of the actual command behaviors of the device, is to append `OPC?` to the command, as done in the example.)

Once you get the control node object, you can call `node.set(value)` to write the value, and call `value=node.get()` to read from it. As a shortcut, `node(value)` is equivalent to `node.set(value)`, and `value=node()` is equivalent to `value=node.get()`. Also, control nodes define Python's `__str__()`, `__float__()`, etc., so `print(node)` and `x = float(node)` will implicitly call `node.get()`.


### Control Node Threading
If a control node has threading methods `run()` or `loop()`, calling `start()` on the node will create a dedicated thread and start it. This is useful for:

- The node can perform tasks independent from the `set()` and `get()` queries, such as PID loops.
- If fetching data is slow, data can be pre-fetched periodically and stored in a cache.

The `run()` function is called once, and then `loop()` is called repeatedly. In the `loop()` function, `sleep()` or similar must be inserted to control the frequency.

The thread is stopped by calling the `stop()` method of the node, or by a global stop request (such as `ControlSystem.stop()` or by signals). The `run()` function must watch for stop requests (by `is_stop_requested()`) and terminate itself when a stop request is made. `loop()` will not be called after a stop.


### Commonly used nodes
Naming convention: `set()`, `get()`, and `do_XXX()` are usual methods to do something. Methods with a noun name return a sub-node.

#### Ethernet, SCPI, and Telnet
##### Loading (already included)
`ControlSystem.load_control_module('Ethernet')`

##### Nodes
- **ethernet(host,port)**: sends and receives text messages through a TCP socket connection
  - set(value): sends the value as encoded text
  - get(): receives a chunk of text
  - do_get_chunk(timeout=None): receives a chunk of text
  - do_get_line(timeout=None): receives a chunk and returns one line (with reconstruction)
  - do_flush_input(): empties the receiving buffer
  - **scpi()** bridges the parent Ethernet connection and holds SCPI configurations
    - **command(cmd)** issues a SCPI command via the parent Ethernet connection
      - set(value=None): sends `cmd value` and waits for a reply
      - get(): sends `cmd?` and waits for a reply, then returns the reply
  - **telnet()** bridges the parent Ethernet connection and holds telnet configurations
    - **command(cmd)** issues a SCPI command via the parent Ethernet connection
      - set(value=None): sends `cmd value line_terminator`, consumes echo
      - get(): sends `cmd line_terminator`, consumes echo, and returns a reply until the next prompt

##### Nodes
- **serial(port='/dev/ttyUSB0',baudrate=9600)**: sends and receives text messages through a serial port
  - set(value): sends the value as encoded text
  - get(): receives a chunk of text
  - do_get_chunk(timeout=None): receives a chunk of text
  - do_get_line(timeout=None): receives a chunk and returns one line (with reconstruction)
  - do_flush_input(): empties the receiving buffer
  - **scpi()** returns the same object as EthernetNode.scpi()

#### HTTP (Web API)
##### Loading (already included)
`ControlSystem.load_control_module('HTTP')`

##### Nodes
- **http(base_url)**:
  - **path(path)**: path string to be appended to the base_url
    - set(value): sends a POST request to `base_url` `path` with `value` as its content
    - get(): sends a GET request to `base_url` `path` and returns the reply content
    - **json()**: 
      - set(value): `value` is a Python object to be converted to JSON
      - get(): receives a JSON document and returns a Python object
    - **value()**: returns ControlValueNode for ramping() etc.
  
#### Shell Command
##### Loading (already included)
`ControlSystem.load_control_module('Shell')`

##### Nodes
- **shell(cmd)**: run a shell command. 
  - set(value): launches `cmd value`, 
  - get(): launches `cmd` and returns the result
  - **value()**: returns ControlValueNode for ramping() etc.
  - **arg(\*args)**: append program arguments to the parent "shell" node. <br>
    Example: `adc0 = ctrl.shell('read_adc', '--timeout=0').arg('--ch=0')`
    - **value()**: returns ControlValueNode for ramping() etc.
    
#### SlowDash server control
##### Loading (already included)
`ControlSystem.load_control_module('HTTP').load_control_module('Slowdash')`

##### Nodes
- **http(url).slowdash()**
  - **ping()**: returns `pong`
  - **channels()**: gets a JSON object of the channel list
  - **data(channels,length=3600)**: gets a JSON object of data for the channels
  - **config()**: gets a JSON object of the project configuration
  - **config_file(name)**: gets or posts a configuration file
    
#### Redis Interface
##### Loading
`ControlSystem.load_control_module('Redis')`

##### Nodes
- **redis(url)**
  - **string(key)**: read and write a simple key-value pair
    - set(value): writes a simple key-value pair
    - get(): returns a value of a simple key-value pair
  - **hash(key)**: read and write a map of key-value pairs
    - set(value): writes a map of key-value pairs
    - get(): returns a hash as a map of key-value pairs
    - **field(name)**: 
      - set(value): writes a single element in the parent hash
      - get(): returns a single element value in the parent hash
  - **json(key)**: 
    - set(value): writes value (Python dict) to Redis JSON
    - get(): returns a Redis JSON as a Python dict
    - **node(path)**: read and write a branch of a JSON object
      - set(value): writes value to a branch of Redis JSON
      - get(): returns a value of a branch of Redis JSON
      - **node(path)**: can do this node iteration recursively
  - **ts(key)**: read and write a time-series, where the value is a list of (t,x) tuples
    - **current()**: 
      - set(value): adds a data point to the parent time-series using the current time
    - **last()**: 
      - get(): returns the last data point as a tuple of (t,x)
      - **value()**: 
        - get(): returns the value of the parent time-series point
      - **time()**: 
        - get(): returns the UNIX time value of the parent time-series point
      - **lapse()**: 
        - get(): returns the number of seconds since the last time-series point
  
#### Other Nodes
- RabbitMQ (using pika and aio-pika)
- MQTT (using paho-mqtt and aio-mqtt)
- Serial (using pyserial)
- VISA (using pyvisa)
- Modbus (using pymodbus)
- LabJack (using LabJackPython, currently supports only U12)
- DummyDevice


### Node Functions
All the control nodes (derived from `slowpy.control.ControlNode`) have the following methods:

- [ControlNode]
  - has_data(): returns True if a value is available for `get()`
  - wait(condition_lambda=None, polling_interval=1, timeout=0): blocks until the `condition_lambda` returns `True` if the lambda is not `None`; if `condition_lambda` is `None`, wait until `has_data()` returns `True`. On timeout, `wait()` returns `None`, and on a stop request, it returns `False`. Otherwise, it returns `True`.
  - sleep(duration_sec): blocks for the duration and returns True unless a stop request is received.
  - is_stop_requested(): returns True if a stop request has been received
  - **readonly()**: makes the node readonly; it returns a node that has only `get()` which calls `parent_node.get()`
  - **writeonly()**: makes the node write only; it returns a node that has only `set()` which calls `parent_node.set()`

Nodes derived from `ControlValueNode` have the following methods:

- [ControlValueNode] -> [ControlNode]
  - **setpoint(limits=[None,None])**: holds the setpoint
    - set(value): holds the value as a set-point, and calls `set(value)` of the parent node.
    - get(): returns the holding set-point value
  - **ramping(change_per_sec)**
      - set(value): starts ramping to the target value in the parent node. If the value is not numeric or not within the limits, it raises an exception
      - get(): returns parent's `get()` 
    - **status()**
      - set(value): `set(0)` will stop the current ramping if it is running
      - get(): returns `True` if ramping is in progress, otherwise returns `False`

Nodes derived from `ControlThreadNode` have the following methods:

- [ControlThreadNode] -> [ControlNode]
  - start(): creates and starts a thread for `run()` and/or `loop()`, if the node has one of these methods (or both)
  - stop(): stops the thread


## Database Interface
Simple example of writing single values to a long-form table:
```python
import time
from slowpy.control import RandomWalkDevice
from slowpy.store import DataStore_PostgreSQL

device = RandomWalkDevice(n=4)
datastore = DataStore_PostgreSQL('postgresql://postgres:postgres@localhost:5432/SlowTestData', table="Test")

while True:
    for ch in range(4):
      value = device.read(ch)
      datastore.append(value, tag='%02d'%ch)

    time.sleep(1)
```

Example of writing a dict of key-values:
```python
while True:
    record = { 'ch%02d'%ch: device.read(ch) for ch in range(4) }
    datastore.append(record)
    time.sleep(1)
```

For SQL databases, the "long format" with UNIX timestamps is used by default. To use other table schemata, specify a user-defined `TableFormat`:
```python
class QuickTourTestDataFormat(LongTableFormat):
    schema_numeric = '(datetime DATETIME, timestamp INTEGER, channel STRING, value REAL, PRIMARY KEY(timestamp, channel))'
    schema_text = '(datetime DATETIME, timestamp INTEGER, channel STRING, value REAL, PRIMARY KEY(timestamp, channel))'

    def insert_numeric_data(self, cur, timestamp, channel, value):
        cur.execute(f'INSERT INTO {self.table} VALUES(CURRENT_TIMESTAMP,%d,?,%f)' % (timestamp, value), (channel,))

    def insert_text_data(self, cur, timestamp, channel, value):
        cur.execute(f'INSERT INTO {self.table} VALUES(CURRENT_TIMESTAMP,%d,?,?' % timestamp), (channel, value))

datastore = DataStore_SQLite('sqlite:///QuickTourTestData.db', table="testdata", table_format=QuickTourTestDataFormat())
```

## Analysis Components
SlowPy provides commonly used data objects such as histograms and graphs. These objects can be directly written to the database using the SlowPy Database Interface described above.

### Histogram
```python
import slowpy as slp
hist = slp.Histogram(100, 0, 10)

device = ...
datastore = ...

while not ControlSystem.is_stop_requested():
  value = device.read(...
  hist.fill(value)
  data_store.append(hist, tag="test_hist")
```

`data_store.append(hist, tag=name)` will create a time-series of histograms (one histogram for each time point). To keep only the latest histogram, use `data_store.update(hist, tag=name)` instead.

### Graph
```python
import slowpy as slp
graph = slp.Graph(['channel', 'value'])

while not ControlSystem.is_stop_requested():
  for ch in range(n_ch):
    value = device.read(ch, ...
    graph.fill(ch, value)
  data_store.append(graph, tag="test_graph")
```

`data_store.append(graph, tag=name)` will create a time-series of graphs (one graph for each time point). To keep only the latest graph, use `data_store.update(graph, tag=name)` instead.

### Trend
```python
import slowpy as slp
rate_trend = slp.RateTrend(length=300, tick=10)

while not ControlSystem.is_stop_requested():
  value = device.read(...
  rate_trend.fill(time.time())

  data_store.append(rate_trend.time_series('test_rate'))
```

## Scpizing Your Device
If your device has some programming capability, such as Raspberry Pi GPIO, an easy way to integrate it into a SlowDash system is to implement the SCPI interface on it. This approach is also useful to integrate other non-Ethernet devices (such as USB) connected to a remote computer.

Here is an example to wrap a device with the Ethernet-SCPI capability:

```python
from slowpy.control import ScpiServer, ScpiAdapter, RandomWalkDevice

class RandomWalkScpiDevice(ScpiAdapter):
    def __init__(self):
        super().__init__(idn='RandomWalk')
        self.device = RandomWalkDevice(n=2)

    def do_command(self, cmd_path, params):
        '''
        parameters:
          cmd_path: array of strings, SCPI command split by ':'
          params: array of strings, SCPI command parameters split by ','
        return value: reply text (even if empty) or None if command is not recognized
        '''
        
        # Implemented Commands: "V0 Value" "V1 Value" "MEASure:V0?" "MEASure:V1?"
        # Common SCPI commands, such as "*IDN?", are implemented in the parent ScpiAdapter class
        if len(params) == 1 and cmd_path[0].startswith('V'):
            try:
                if cmd_path[0] == 'V0':
                    self.device.write(0, float(params[0]))
                elif cmd_path[0] == 'V1':
                    self.device.write(1, float(params[0]))
                else:
                    self.push_error(f'invalid command {cmd_path[0]}')
            except:
                self.push_error(f'bad parameter value: {params[0]}')
            return ''
            
        elif len(cmd_path) == 2 and cmd_path[0].startswith('MEAS'):
            if cmd_path[1] == 'V0?':
                return self.device.read(0)
            elif cmd_path[1] == 'V1?':
                return self.device.read(1)
            else:
                self.push_error(f'invalid command {cmd_path[0]}')
            return ''
            
        return None
        
device = RandomWalkScpiDevice()
server = ScpiServer(device, port=17674)
server.start()
```

Make this code start automatically on PC boot in your favorite way (`/etc/rc.local`, Docker, ...).

If SlowPy Control Nodes are already available for the device, the nodes can be directly mapped to the SCPI interface:
```python
from slowpy.control import ControlSystem, ScpiServer, ScpiAdapter

ControlSystem.import_control_module('DummyDevice')
device = ControlSystem().randomwalk_device()

adapter = ScpiAdapter(idn='RandomWalk')
adapter.bind_nodes([
    ('CONFIGure:WALK', device.walk().setpoint(limits=(0,None))),
    ('CONFIGure:DECAY', device.decay().setpoint(limits=(0,1))),
    ('V0', device.ch(0).setpoint()),
    ('V1', device.ch(1).setpoint()),
    ('MEASure:V0', device.ch(0).readonly()),
    ('MEASure:V1', device.ch(1).readonly()),
])

server = ScpiServer(adapter, port=17674)
server.start()
```

# SlowTask: GUI-Script Binding
SlowTask is a user Python script placed under the SlowDash config directory with a name like `slowtask-XXX.py`. SlowDash GUI can start/stop the script, call functions defined in the script, and bind control variables in the script to GUI elements. The SlowPy library was designed for use in user task scripts, but this is not a requirement.


## Starting, Stopping, and Reloading the Slow-Task Scripts
SlowTask script files (such as `slowtask-test.py`) are placed under the project configuration directory. By default, tasks are "listed" in the Task Manager panel of the SlowDash web page, but they will not be "loaded" until the `start` button is clicked. Auto-loading can be set by making an entry in the SlowDash configuration file (`SlowdashProject.yaml`):
```yaml
slowdash_project:
  ...

  task:
    name: test
    auto_load: true
    parameters:
      default_ramping_speed: 0.1

  system:
    our_security_is_perfect: false
```

The parameters are optional, and if given, these will be passed to the `_initialize(params)` function of the script (described later).

Setting `system/our_security_is_perfect` to `true` will enable editing of the Python scripts on the SlowDash web page. While this is convenient, please keep in mind what it means. Python scripts can do anything, such as `system("rm *")`. You can only use this feature when access is strictly controlled. Some secure systems run processes only in Docker containers, where the container system runs on a virtual machine (in case the container is compromised) inside a firewall that accepts only VPN or SSH connections from listed addresses. Additionally, to prevent unintended destruction by novice operators, it may be safer to run two instances of SlowDash: one with full features and one with limited operations (without or only with selected tasks). The `slowdash` command has an option to specify which configuration file to use.


## Callback Functions (Command Task)
Functions in SlowTask scripts can be called from the SlowDash GUI. If a script (named `test`) has a function like this
```python
def destroy_apparatus():
  #... do your work here
```
This can be called from the SlowDash GUI in several ways.

#### HTML Form Panel

From an HTML form panel in SlowPlot, clicking a `<button>` with a name of the task module and the function will call the function:
```html
<form>
  <input type="submit" name="test.destroy_apparatus()" value="Finish">
</form>
```
Here, the parentheses at the end of the button name indicate that this button is bound to a SlowTask function.

The prefix (`test.` in this example) is the module name, which is taken from the module file name by stripping the beginning 'slowtask-'. If the module name includes `-`, those will be replaced with `_`. The prefix can be explicitly specified in the `SlowdashProject.yaml` configuration file as:
```yaml
  task:
    name: another_test
    namespace:
      prefix: test.
```
Note that the dot is a part of the prefix.

SlowTask functions can take parameters:
```python
def set_V0(voltage:float, ramping:float):
  #... do your work here
```
and these parameter values are taken from the form input values:
```html
<form>
  Voltage: <input type="number" name="voltage" value="0"><br>
  Ramping: <input type="number" name="ramping" value="1"><br>
  <input type="submit" name="test.set_V0()" value="Set">
</form>
```

By using the type notation in the SlowTask function as shown above, the parameter values are converted to the specified types. If the value literal cannot be converted to the specified type, an error response will be returned to the browser and the SlowTask function will not be called.

The SlowTask function can be either the standard `def` or `async def`.

It is possible to place multiple buttons in one form:
```html
<form>
  Ramping: <input type="number" name="ramping" value="1" style="width:5em">/sec
  <p>
  V0: <input type="number" name="V0" value="0"><input type="submit" name="parallel test.set_V0()" value="Set"><br>
  V1: <input type="number" name="V1" value="0"><input type="submit" name="parallel test.set_V1()" value="Set"><br>
  V2: <input type="number" name="V2" value="0"><input type="submit" name="parallel test.set_V2()" value="Set"><br>
  V3: <input type="number" name="V3" value="0"><input type="submit" name="parallel test.set_V3()" value="Set"><br>
  <p>
  <input type="submit" name="test.set_all()" value="Set All">
  <input type="submit" name="parallel test.stop()" value="Stop Ramping"><br>    
</form>
```
```python
def set_V0(V0:float, ramping:float):
  #...

def set_V1(V1:float, ramping:float):
  #...

#...
```
The input values on the Web form will be bound to the function parameters based on the names (`<input name="V0">` will be bound to the `V0` parameter).

In the example above, some functions have the `parallel` qualifier: by default, if a previous function call is in execution, the next action cannot be accepted to avoid multi-threading issues in the user code. The `parallel` qualifier indicates that this function can run in parallel to others. Another common qualifier is `await`, which instructs the web browser to wait for completion of the function execution before doing anything else (therefore, the browser will look frozen).

#### Canvas Panel
On a canvas panel, a button to call a task can be placed by:
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

For functions with parameters, a form can be used:
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

For more details, see the [UI Panels section](Panels.html).

## Thread Functions (Routine Task)
If a SlowTask script has functions of `_initialize(params)`, `_finalize()`, `_run()`, and/or `_loop()`, one dedicated thread will be created, and these functions are called in a sequence:

| function | description |
|---|---|
| `_initialize(params)` | called once when the script is loaded. The `params` values are given by the SlowDash configuration. |
| `_run()` | called once after `_initialize()`. If `_run()` is defined, `_halt()` should also be defined to stop the `_run()` function. `_halt()` will be called by SlowDash when the user stops the system. |
| `_loop()` | called repeatedly after `_initialize()`, until the user stops the system. To control the intervals, the function usually contains `time.sleep()` or equivalent. |
| `_finalize()` | called once after `_run()` or `_loop()` |

These functions can be either the standard `def` or `async def`.

## Control Variable Exporting
Control variables can be exported to other SlowDash components (typically web browsers) so that the other components can call `get()` and `set()` of the nodes. 
```python
from slowpy.control import control_system as ctrl
V0 = ctrl.ethernet(host, port).scpi().command("V")
ctrl.export(V0, 'V0')
```
The exported nodes are listed in the channel list and can be accessed in the same way as data stored in databases, except that only "current" values are available. Typically these are used in "Single Scalar" display panels, or in HTML panels:
```html
<form>
  V0: <span sd-value="V0"></span>
</form>
```

Python `dict` and `dataclass` instances can be exported in the same way. Instances of `class` can also be exported, but with some restrictions (e.g., `vars()` must be able to serialize the instance). SlowPy analysis elements, such as histograms and graphs, are also accepted.
```python
from slowpy.control import control_system as ctrl
V0 = ctrl.ethernet(host, port).scpi().command("V")
ctrl.export(V0, name='V0')

from slowpy import Histogram
h = Histogram(100, 0, 20)
ctrl.export(h, name='hist')

def _loop():
    h.fill(V0.get())
    ctrl.sleep(1)
```

To export a variable not of these types, make a temporary control node variable to wrap it:
```python
class RampingStatusNode(ControlNode):
    def get(self):
        return {
            'columns': [ 'Channel', 'Value', 'Ramping' ],
            'table': [
                [ 'Ch0', float(V0), 'Yes' if V0.ramping().status().get() else 'No' ],
                [ 'Ch1', float(V1), 'Yes' if V1.ramping().status().get() else 'No' ],
                [ 'Ch2', float(V2), 'Yes' if V2.ramping().status().get() else 'No' ],
                [ 'Ch3', float(V3), 'Yes' if V3.ramping().status().get() else 'No' ]
            ]
        }
    
ctrl.export(RampingStatusNode(), 'Status')
```

## Control Variable Binding (Streaming / Live Updating)
The current values of exported variables are "pulled" by the other components. In addition, the values can be "pushed" to the others (data streaming).
```python
from slowpy.control import control_system as ctrl

V0 = ctrl.ethernet(host, port).scpi().command("V")
ctrl.export(V0, 'V0')            # exporting to be pulled

async def _loop():
    await ctrl.aio_publish(V0)   # publishing (pushing to subscribers)
    await ctrl.aio_sleep(1)
```
If the variable is already exported, the same export name is used. Otherwise, the name must be provided as a `name` argument of the `aio_publish()` function. In addition to the export-able variables, `aio_publish()` accepts many other types, including Python numbers.
```python
import random
from slowpy.control import control_system as ctrl

x = 0
async def _loop():
    global x
    x = x + random.random()
    await ctrl.aio_publish(x, name="RandomWalk")
    await ctrl.aio_sleep(1)
```

In addition to accessing the exported variables in the same way as data in databases, the variables can be directly "bound" in web browsers. If a SlowTask control variable is bound in SlowDash HTML, changes to the variable on the browser call the `.set()` method of the SlowTask variable.
```html
<form>
  Readout Frequency: <input type="number" sd-value="readout_frequency" sd-live="true">
  ...
</form>
```
```python
from slowpy.control import control_system as ctrl

readout_frequency = ctrl.value(1.0)
ctrl.export(readout_frequency, 'readout_frequency')   # to be set by GUI

V = ctrl.ethernet(host, port).scpi().command("V")

async def _loop():
    await ctrl.aio_publish(V, name='V')
    await ctrl.aio_sleep(readout_frequency.get())
```
In HTML, `sd-live="true"` indicates that changes of the value on the browser will trigger calling the `.set()` method of the bound variable.

More examples can be found in `ExampleProjects/Streaming`.

## Matplotlib Integration
Instances of Matplotlib Figure can be directly published. 
```python
import matplotlib.pyplot as plt
from slowpy.control import control_system as ctrl

async def _loop():
    fig, axes = plt.subplots(2, 2)
    #... draw plots in the usual way

    await ctrl.aio_publish(fig, name='mpl')

    plt.close()  # If a figure is created in a loop, it must be closed every time.
    await ctrl.aio_sleep(1)
```
When a Matplotlib figure is published, a SlowDash layout (usually a `slowplot-XXX.json` file under `config`) is created dynamically for the same axes layout as the figure. The plotting objects in the figure are extracted and converted to SlowDash objects before publishing.

# Distributed System / Network Deployment
## SlowDash Interconnect
## SlowTask Scpization
