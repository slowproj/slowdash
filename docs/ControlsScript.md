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
#### Controlling an ethernet voltmeter with SCPI command
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

## Analysis Components
SlowPy provides commonly used data objects such as histograms and graphs. These objects can be directly written to the database using the SlowPy Daabase Interface described above.

### Histogram
### Graph
### Trend



# SlowTask: Slowdash GUI-Script Interconnect
SlowTask is a user Python script placed under the SlowDash config directory with a name like `slowtask-XXX.py`. SlowDash GUI can start/stop the script, call functions defined in the script, and bind control variables in the script to GUI elements. Using the SlowPy library from a SlowTask script is assumed for this design, but this is not a requirement.

## Callback Functions (Command Task)
Functions in SlowTask scripts can be called from SlowDash GUI. If a script has a function like this
```python
def destroy_apparatus():
  #... do your work here
```
This can be called from SlowDash GUI, from a HTML form panel or from a Canvas panel:


## Thread Functions (Routine Task)
## Control Variable Binding



