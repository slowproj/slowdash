---
title: Controls Script
---

# Overview
## Applications
- Send commands and receive data to/from external systems (either software or hardware), including:
  - Another concurrent systems (DAQ system etc.)
    - Through a messaging system, such as Redis, AMQP, Kafka, ZMQ, ...
    - Through a HTTP Get/Post, or Socket messages
    - By running a shell command
  - Measurement devices that accept commands
    - SCPI measurement devices with ethernet interface
    - Anything that can be used from Python
      - Raspberry-Pi GPIO, I2C, SPI, ...
      - USB devices with a vendor library
  - Another SlowDash instance for distributed systems
- Analyze data in real-time, construct histograms etc., issue alarms
- Store raw and analyzed values (including histograms) to database systems

## Structure
<img src="fig/ContrlScript-UserTask.png" width="40%">

- Controls are implemented as user task python script.
- User task script is a normal Python script. Executable independently.
- Panels on the Slowdash GUI, built by users, can call functions defined in user task scripts.
- A Python library, `slowpy`, is provided to be imported by the user task scripts, for:
  - Simple unified methods to control external systems
  - Data classes such as histograms, graphs, time-series, etc.
  - Data storage interface to store the data objects, as well as raw data from the external systems

## Simple Examples
#### Controlling a voltmeter with SCPI commands over Ethernet
```python
from slowpy.control import ControlSystem
ctrl = ControlSystem()

# make a control node for a SCIP command of "MEAS:V0" on a device at 182.168.1.43
V0 = ctrl.ethernet(host='192.168.1.43', port=17674).scpi().command('MEAS:V0', set_format='V0 {};*OPC?')

# write a value to the control node: this will issue a SCPI command "V0 10;*OPC?"
V0.set(10)

while True:
  # read a value from the control node, with a SCPI command "MEAS:V?"
  value = V0.get()
  ...
```

#### Writing a data value to PostgreSQL database (using a default schema)
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
Then clicking the `Set` button will call the function `set_V0()` with a parameter in the `value` input field. 

#### Displaying the readout values on the SlowDash panels
For a control node `V0`, and `V1`, defining `_export()` function in the User Task Script will export these node values, making them available in SlowDash GUI in the same way as the values stored in database.
```python
device = ctrl.ethernet(host='192.168.1.43', port=17674).scpi()
V0 = device.command('MEAS:V0', set_format='V0 {};*OPC?')
V1 = device.command('MEAS:V1', set_format='V1 {};*OPC?')
def _export():
    return [
        ('V0', V0),
        ('V1', V1)
    ]
```
Only the "current" values are available in this way. If you need historical values, store the values in a database.


## Demonstration Example Project
In `slowdash/ExampleProjects/SlowTask` there is a slowdash project to demonstrate some of the features described here.
```console
$ cd slowdash/ExampleProjects/SlowTask
$ slowdash --port=18881
```
or
```console
$ cd slowdash/ExampleProjects/SlowTask
$ docker-compose up
```


# SlowPy: Controls Library
SlowPy is a Python library (module) that provides functions like:

- connecting external concurrent systems and/or measurement hardware
- histograms, graphs, etc.
- storing raw values, time-series and histograms/graphs to database in a way that SlowDash can easily handle.

The SlowPy library is included in the SlowDash package, under `slowdash/lib/slowpy`. By running `source slowdash/bin/slowdash-bashrc`, as instructed in the Installation section, this path will be included in the environmental variable `PYTHONPAH`, so that users can use the library without modifying users system. It is also possible to install the library in a usual way: you can do `pip install slowdas/lib/slowpy` to install SlowPy into your Python environment. You might want to combine this with `pyenv` not to mess up your Python.

## Controls
SlowPy provides an unified interface to connect external software systems and hardware devices; everything will be mapped into a single "ControlTree" where each node has `set()` and `get()`. The tree represents logical structure of the system, for example, a SCPI command of `MEAS:V` to a voltmeter connected to an ethernet would be addressed like `ControlSystem.ethernet(host, port).scpi().command('MEAS:V')`, and `set(value)` to this node will send a SCPI command of `MEAS:V?` to the voltmeter. The `get()` method makes a read access and returns a value.

Plugin modules can dynamically add branches to the control tree. For example, Redis plugin adds the `redis()` node and a number of sub-branches for functions that Redis provides, such as hash, json and time-series. Plugins are loaded to a node, not (necessarily) to the root ControlSystem; for example, a plugin that uses ethernet is loaded to an ethernet node, creating a sub-branch under the ethernet node, and the plugin can make use of the function provided by the ethernet node such as `send()` (which is `set()` of the node) and `receive()` (which is `get()`).

### Example
Here is an example of using SlowPy Controls. In this example, we use a power supply device that accepts the SCPI commands through ethernet.

```python
from slowpy.control import ControlSystem
ctrl = ControlSystem()

# make a control node for a SCIP command of "MEAS:V0" on a device at 182.168.1.32
V0 = ctrl.ethernet(host='192.168.1.43', port=17674).scpi().command('MEAS:V0', set_format='V0 {};*OPC?')

# write a value to the control node: this will issue a SCPI command "V0 10;*OPC?"
V0.set(10)

while True:
  # read a value from the control node, with a SCPI command "MEAS:V"
  value = V0.get()
  ...
```
A common start would be importing the `slowpy.control`, and then creating an instance of the `ControlSystem` class.

The `ControlSystem` already includes the `Ethernet` plugin, but if it were not, the loading plugin code would have been:
```python
ctrl.load_control_module('Ethernet')
```
This will search for a file named `control_Ethernet.py` from search directories, load it, and inject the `ethernet()` Python method to the node class that loaded the plugin (which is ControlSystem in this case). The Ethernet plugin already includes sub-branches for SCPI; for specific protocols not already included, a plugin would be loaded onto the Ethernet node.

Each node constructor takes parameters. In this example, the ethernet node, which sends and receives data to/from the ethernet, takes the host/IP and port parameters, and a SCPI command node, which is bound to a specific SCPI command, takes the SCPI command parameter with optional `set_format` which overrides the default SCPI command for writing. (The default SCPI command to be written/read `.scpi().command(CMD)` are `CMD` and `CMD?`, respectively. Often write operations should wait for the command completion, and SlowPy expects a return value from each command. A technique to do it, regardless to the actual command behaviors of the device, is to append `OPC?` to the command, as done in the example.)

Once you get the control node object, you can call `node.set(value)` to write the value, and call `value=node.get()` to read from it. As a shortcut, `node(value)` is equivalent to `node.set(value)`, and `value=node()` is equivalent to `value=node.get()`. Also control nodes define Python's `__str__()`, `__float__()`, etc., so `print(node)` and `x = float(node)` will implicitly call `node.get()`.

### Commonly used nodes
Naming convention: `set()`, `get()`, and `do_XXX()` are usual methods to do something. Methods with a noun name return a sub-node.

#### Ethernet, SCPI and Telnet
##### Loading
`ControlSystem.load_control_module('Ethernet')`: already included

##### Nodes
- **ethernet(host,port)**: sends and receives text messages through a TCP socket connection
  - set(value): sends the value as encoded text
  - get(): receives a chunk of text
  - do_get_chunk(timeout=None): receives a chunk of text
  - do_get_line(timeout=None): receives a chunk and returns one line (with reconstruction)
  - do_flush_input(): empties the receiving buffer
  - **scpi()** bridges the parent ethernet connection and holds SCPI configurations
    - **command(cmd)** issue a SCPI command via the parent ethernet connection
      - set(value=None): sends `cmd value` and waits for a reply
      - get(): sends `cmd?` and waits for a reply, then returns the reply
  - **telnet()** bridges the parent ethernet connection and holds telnet configurations
    - **command(cmd)** issue a SCPI command via the parent ethernet connection
      - set(value=None): sends `cmd value line_terminator`, consumes echo
      - get(): sends `cmd line_terminator`, consumes echo, and returns a reply until the next prompt

#### HTTP (Web API)
##### Loading
`ControlSystem.load_control_module('HTTP')`

##### Nodes
- **http(base_url)**:
  - **path(path)**: path string to be appended to the base_url
    - set(value): sends a POST request to `base_url` `path` with `value` as its content
    - get(): sends a GET request to `base_url` `path` and return the reply content
  
#### Shell Command
##### Loading
`ControlSystem.load_control_module('Shell')`: already included

##### Nodes
- **shell(cmd)**: run a shell command. 
  - set(value): launches `cmd value`, 
  - get(): launches `cmd` and returns the result
  - **arg(\*args)**: append program arguments to the parent "shell" node. <br>
    Example: `adc0 = ctrl.shell('read_adc', '--timeout=0').arg('--ch=0')`
    
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
    - **filed(name)**: 
      - set(value): writes a single element in the parent hash
      - get(): returns a single element value in the parent hash
  - **json(key)**: 
    - set(value): writes value (Python dict) to Redis JSON
    - get(): returns a Redis JSON as Python dict
    - **node(path)**: read and write a branch of JSON object
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
  
### Node Functions
All the control nodes (derived from slowpy.control.ControlNode) have the following methods:

- (ControlNode)
  - **setpoint()**: holds the setpoint
    - set(value): holds the value as a set-point, and calls `set(value)` of the parent node.
    - get(): returns the holding set-point value
  - **ramping(change_per_sec)**
      - set(value): starts ramping to the target value in the parent node
      - get(): returns parent's `get()` 
    - **status()**
      - set(value): `set(0)` will stop the current ramping if it is running
      - get(): returns `True` if rumping is in progress, otherwise returns `False`
  - has_data(): returns True if a value is available for `get()`
  - wait_until(condition_lambda, polling_interval=1, timeout=0): blocks until the condition_lambda returns True
  - sleep(duration_sec): blocks for the duration and returns True unless ControlSystem receives a stop request


## Database Interface
Simple example of writing single values to a long form table:
```python
import time
from slowpy.control import DummyDevice_RandomWalk
from slowpy.store import DataStore_PostgreSQL

device = DummyDevice_RandomWalk(n=4)
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

For SQL databases, the "long format" with UNIX timestamps is used by default. To use other table schemata, specify an user defined `TableFormat`:
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
SlowPy provides commonly used data objects such as histograms and graphs. These objects can be directly written to the database using the SlowPy Daabase Interface described above.

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
If your device has some programming capability, such as Raspberry-Pi GPIO, an easy way to integrate it into a SlowDash system is to implement the SCPI interface on it. This approach is also useful to use USB devices connected to a remote computer. 

Here is an example to wrap a (dummy) device with the ethernet-SCPI capability:

```python
from slowpy.control import ScpiDevice, SerialDeviceEthernetServer
from slowpy.control import DummyDevice_RandomWalk

class MyFantasticScpiDevice(ScpiDevice):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.device = DummyDevice_RandomWalk(n=4)

    def process_scpi_command(self, cmd_path, params):
        '''
        "meas:V0?" -> cmd_path=['MEAS', 'V0?', None, ...], params=[None, None, ...]
        "v0 3.21" -> cmd_path=['V0', None, None, ...], params=['3.2', None, ...]
        '''
        if cmd_path[0] == '*IDN?':
            return 'Dummy SCPI Device'
        elif cmd_path[0] == '*OPC?':
            return '1'
        elif cmd_path[0][0:4] == 'MEAS' and cmd_path[1] == 'V0?':
            return '%f' % self.device.read(0)
        elif cmd_path[0][0:4] == 'MEAS' and cmd_path[1] == 'V1?':
          ...

if __name__ == '__main__':
    from optparse import OptionParser
    optionparser = OptionParser()
    optionparser.add_option(
        '--port', action='store', dest='port', type='int', default=17674,
        help='port number'
    )
    (opts, args) = optionparser.parse_args()
    
    device = MyFantasticScpiDevice()
    server = SerialDeviceEthernetServer(device, port=opts.port)
    server.start()
```

Make this code start automatically on PC boot in your favorite way (`/etc/rc.local`, Docker, ...).


# SlowTask: Slowdash GUI-Script Interconnect
SlowTask is a user Python script placed under the SlowDash config directory with a name like `slowtask-XXX.py`. SlowDash GUI can start/stop the script, call functions defined in the script, and bind control variables in the script to GUI elements. Using the SlowPy library from a SlowTask script is assumed for this design, but this is not a requirement.


## Starting, Stopping and Reloading the Slow-Task Scripts
SlowTask script files (such as `slowtask-test.py`) are placed under the project configuration directory. The files are enabled by making an entry in the project configuration file (`SlowdashProject.yaml`):
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
Tasks will be listed in the Task Manager table of SlowDash page, and can be controlled from there.

The parameters are optional, and if given, these will be passed to the `_initialize(params)` function of the script (described later).

By setting `system/our_security_is_peferct` to `true` will enable editing of the Python scripts on the SlowDash web page. While this is convenient, be aware what it means. Python scripts can do anything, such as `system("rm *")`. Enable this feature only when the access is strictly controlled. Some careful systems run processes only in Docker containers, where the container system runs on a virtual machine (in case the container is cracked) inside a firewall which accepts only VPN or SSH accesses from listed addresses. On top of that, in order to prevent unintended destruction by novice operators, it would be safer to run two instances of SlowDash, one with full features and one with limited operations (no or selected tasks); the `slowdash` command have an option to specify which configuration file to use.


## Callback Functions (Command Task)
Functions in SlowTask scripts can be called from SlowDash GUI. If a script (of name `test`) has a function like this
```python
def destroy_apparatus():
  #... do your work here
```
This can be called from SlowDash GUI in several ways.

#### HTML Form Panel

From a HTML form panel in SlowPlot, clicking a `<button>` with a name of the task module and the function will call the function:
```html
<form>
  <input type="submit" name="test.destroy_apparatus()" value="Finish">
</form>
```
Here the parenthesis at the and of the button name indicate that this button is bound to a SlowTask function.

SlowTask functions can take parameters:
```python
def set_V0(voltage, ramping):
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

It is possible to place multiple buttons in one form:
```html
<form>
  Ramping: <input type="number" name="ramping" value="1" style="width:5em">/sec
  <p>
  V0: <input type="number" name="V0" value="0"><input type="submit" name="async test.set_V0()" value="Set"><br>
  V1: <input type="number" name="V1" value="0"><input type="submit" name="async test.set_V1()" value="Set"><br>
  V2: <input type="number" name="V2" value="0"><input type="submit" name="async test.set_V2()" value="Set"><br>
  V3: <input type="number" name="V3" value="0"><input type="submit" name="async test.set_V3()" value="Set"><br>
  <p>
  <input type="submit" name="test.set_all()" value="Set All">
  <input type="submit" name="async test.stop()" value="Stop Ramping"><br>    
</form>
```
In that case, some input fields might not be used by some buttons. Since all the input field values are passed to the function parameters, it may cause a Python error of unexpected parameters. To absorb the unused parameters, a best practice is always adding `**kwargs` to the SlowTask function parameters:
```python
def set_V0(V0, ramping, **kwargs):
  #... do your work here
```

In the example above, some functions have the `async` qualifier: by default, if a previous function call is in execution, a next action cannot be accepted to avoid multi-threading issues in the user code. The `async` qualifier indicates that this function call can be run in parallel to others. Another common qualifier is `await`, which instruct the GUI to wait for completion of the function execution before doing any other things (therefore it will look frozen).

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
            "title": " Injection Flow",
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
If a SlowTask script has functions of `_initialize(params)`, `_finalize()`, `_run()`, and/or `_loop()`, one dedicated thread will be created and these function are called in a sequence:

| function | description |
|---|---|
| `_initialize(params)` | called once when the script is loaded. The `params` values are given by the SlowDash configuration. |
| `_run()` | called once after `_initialize()`. If `_run()` is defined, `_halt()` should be also defined to stop the `_run()` function. `_halt()` will be called by SlowDash when the user stops the system. |
| `_loop()` | called repeatedly after `_initialize()`, until the user stops the system. To control the intervals, the function usually contains `time.sleep()` or equivalent. |
| `_finalize()` | called once after `_run()` or `_loop()` |

## Control Variable Binding
Control variables (instances of the Control Node classes) can be bound to GUI elements if a SlowTask script exports them with the `_export()` function:
```python
def _export():
    return [
      ('V0', V0),
      ('V1', V1),
      ('V2', V2),
      ('V3', V3)
    ]
```
Here the return value is a list of tuples of (name, control_node_variable). In the GUI, the exported entries can be used in the same way as data from a database. To export a variable that is not a control node, wrapping it with a control node is easy:
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
    
def _export():
    return [
        ('V0', V0),
        ('V1', V1),
        ('V2', V2),
        ('V3', V3),
        ('Status', StatusNode())
    ]
```
Here the new node `StatusNode` returns a table object.
