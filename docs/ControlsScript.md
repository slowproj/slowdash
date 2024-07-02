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
  - User analysis code that runs on streaming data

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

# make a control node for a SCIP command of "MEAS:V0" on a device at 182.168.1.32
V0 = ctrl.ethernet(host='192.168.1.43', port=17674).scpi('MEAS:V0', set_format='V0 {};*OPC?')

# write a value to the control node: this will issue a SCPI command "V0 10;*OPC?"
V0.set(10)

while True:
  # read a value from the control node, with a SCPI command "MEAS:V"
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
  V0: <input name="value"><input type="submit" name="test.set_V0()" value="Set"><br>
</form>
```
Then clicking the `Set` button will call the function `set_V0()` with a parameter in the `value` input field. 

#### Displaying the readout values on the SlowDash panels
For a control node `V0`, and `V1`, defining `_export()` function in the User Task Script will export these node values, making them available in SlowDash GUI in the same way as the values stored in database.
```python
V0 = ctrl.ethernet(host='192.168.1.43', port=17674).scpi('MEAS:V0', set_format='V0 {};*OPC?')
V1 = ctrl.ethernet(host='192.168.1.43', port=17674).scpi('MEAS:V1', set_format='V1 {};*OPC?')
def _export():
    return [
        ('V0', V0),
        ('V1', Vi))
    ]
```
Only the "current" values are available in this way. If you need historical values, store the values in a database.

# SlowPy: Controls Library
SlowPy is a Python library (module) that provides functions like:

- connecting external concurrent systems and/or measurement hardware
- histograms, graphs, etc.
- storing raw values, time-series and histograms/graphs to database in a way that SlowDash can easily handle.

The SlowPy library is included in the SlowDash package, under `slowdash/lib/slowpy`. By running `source slowdash/bin/slowdash-bashrc`, as instructed in the Installation section, this path will be included in the environmental variable `PYTHONPAH`, so that users can use the library without modifying users system. It is also possible to install the library in a usual way: you can do `pip install slowdas/lib/slowpy` to install SlowPy into your Python environment. You might want to combine this with `pyenv` not to mess up your Python.

## Controls
SlowPy provides an unified interface to connect external software systems and hardware devices; everything will be mapped into a single "ControlTree" where each node has `set()` and `get()`. The tree represents logical structure of the system, for example, a SCPI command of `MEAS:V` to a voltmeter connected to an ethernet would be addressed like `ControlSystem.ethernet(host, port).scpi('MEAS:V')`, and `set(value)` to this node will send a SCPI command of `MEAS:V?` to the voltmeter. The `get()` method makes a read access and returns a value.

Plugin modules can dynamically add branches to the control tree. For example, Redis plugin adds the `redis()` node and a number of sub-branches for functions that Redis provides, such as hash, json and time-series. Plugins are loaded to a node, not (necessarily) to the root ControlSystem; for example, a plugin that uses ethernet is loaded to an ethernet node, creating a sub-branch under the ethernet node, and the plugin can make use of the function provided by the ethernet node such as `send()` (which is `set()` of the node) and `receive()` (which is `get()`).

### Example
Here is an example of using SlowPy Controls. In this example, we use a power supply device that accepts the SCPI commands through ethernet.

```python
from slowpy.control import ControlSystem
ctrl = ControlSystem()

# make a control node for a SCIP command of "MEAS:V0" on a device at 182.168.1.32
V0 = ctrl.ethernet(host='192.168.1.43', port=17674).scpi('MEAS:V0', set_format='V0 {};*OPC?')

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

Each node constructor takes parameters. In this example, the ethernet node, which sends and receives data to/from the ethernet, takes the host/IP and port parameters, and a SCPI node, which is bound to a specific SCPI command, takes the SCPI command parameter with optional `set_format` which overrides the default SCPI command for writing. (The default SCPI command to be written/read `.scpi(CMD)` are `CMD` and `CMD?`, respectively. Often write operations should wait for the command completion, and SlowPy expects a return value from each command. A technique to do it, regardless to the actual command behaviors of the device, is to append `OPC?` to the command, as done in the example.)

Once you get the control node object, you can call `node.set(value)` to write the value, and call `value=node.get()` to read from it. As a shortcut, `node(value)` is equivalent to `node.set(value)`, and `value=node()` is equivalent to `value=node.get()`. Also control nodes define Python's `__str__()`, `__float__()`, etc., so `print(node)` and `x = float(node)` will implicitly call `node.get()`.

### Commonly used nodes
Naming convention: `set()`, `get()`, and `do_XXX()` are usual methods to do something. Methods with a noun name return a sub-node.

#### Ethenet and SCPI
##### Loading
`ControlSystem.load_control_module('Ethernet')`: already included

##### Nodes
- **ethernet(host,port)**: sends and receives text messages through a TCP socket connection
  - set(value): sends the value with adding a line delimiter (typically CR or LF)
  - get(): receives a line terminated by a line delimiter and returns it
  - do_flush(): empty the receiving buffer
  - **scpi(cmd)** [sub-node]: issue a SCPI command via the parent ethernet connection
    - set(value): sends `cmd value` and waits for a reply
    - get(): sends `cmd?` and waits for a reply, then returns the reply

#### Shell Command
##### Loading
`ControlSystem.load_control_module('Shell')`: already included

##### Nodes
- **shell(cmd)**: run a shell command. 
  - set(\*arg) launches `cmd arg`, 
  - get() launches `cmd` and returns the result
  - **arg(\*args)**: append program arguments to the parent "shell" node. Example: `shell('read_adc', '--timeout=0').arg('--ch=0').get()`
  
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
```python
import time
from slowpy.control import DummyDevice_RandomWalk
from slowpy.store import DataStore_PostgreSQL

device = DummyDevice_RandomWalk(n=4)
datastore = DataStore_PostgreSQL('postgresql://postgres:postgres@localhost:5432/SlowTestData', table="Test")

while True:
    records = { 'ch%01d'%ch: device.read(ch) for ch in range(4) }
    print(records)

    datastore.append(records)
    
    time.sleep(1)
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
  data_store.write(hist, tag="test_hist")
```

### Graph
```python
import slowpy as slp
graph = slp.Graph(['channel', 'value'])

while not ControlSystem.is_stop_requested():
  for ch in range(n_ch):
    value = device.read(ch, ...
    graph.fill(ch, value)
  data_store.write(graph, tag="test_graph")
```

### Trend
```python
import slowpy as slp
rate_trend = slp.RateTrend(length=300, tick=10)

while not ControlSystem.is_stop_requested():
  value = device.read(...
  rate_trend.fill(time.time())

  data_store.write(rate_trend.time_series('test_rate'))
```




# SlowTask: Slowdash GUI-Script Interconnect
SlowTask is a user Python script placed under the SlowDash config directory with a name like `slowtask-XXX.py`. SlowDash GUI can start/stop the script, call functions defined in the script, and bind control variables in the script to GUI elements. Using the SlowPy library from a SlowTask script is assumed for this design, but this is not a requirement.

## Callback Functions (Command Task)
Functions in SlowTask scripts can be called from SlowDash GUI. If a script (of name `test`) has a function like this
```python
def destroy_apparatus():
  #... do your work here
```
This can be called from SlowDash GUI in several ways.

From a HTML form panel in SlowPlot, clicking a `<button>` with a name of the task module and the function will call the function:
```html
<form>
  <input type="submit" name="test.set_V0()" value="Set">
</form>
```
Here the parenthesis at the and of the button name indicates that this button is bound to a SlowTask function.

SlowTask functions can take parameters:
```python
def set_V0(voltage, ramping):
  #... do your work here
```
and these parameter values are taken from the form values (typically from `<input>` entries):
```html
<form>
  Voltage: <input type="number" name="voltage" value="0"><br>
  Ramping: <input type="number" name="ramping" value="1"><br>
  <input type="submit" name="test.set_V0()" value="Set">
</form>
```

It is possible to place multiple buttons in one form. 
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

The canvas panel can have a form to do the same as the HTML form panel. See the UI Panels section for details.

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


## Listing, Starting, Stopping and Reloading the Slow-Task Scripts
All SlowTask scripts (python file placed under project configuration directory with a name of `slowtask-XXX.py`) are automatically listed in the SlowDash Task Manager. Here users can manually start and stop the script. Starting again will reload the script.

Scripts can be started automatically, by making an entry in the `SlowdashProject.yaml`:
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
In the Slowdash configuration you can also pass parameters to the `_initialize()` function.

By setting `system/our_security_is_peferct` to `true` will enable editing of the Python scripts on the SlowDash web page. While this is convenient, be aware what this means. Python scripts can do anything, such as `system("rm *")`. Enable this feature only when the access is strictly controlled. Some careful systems run processes only in Docker containers, where the container system runs on a virtual machine (in case the container is cracked) inside a firewall.
