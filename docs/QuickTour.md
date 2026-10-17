---
title: Quick Tour
---

# Course Overview
This tour demonstrates how to use SlowDash with SQLite as the data backend, which requires no server setup. All files created during this tour are contained within a single project directory and can be completely removed by simply deleting that directory.

### Menu
- Configure a project by defining the user data schema
- Run SlowDash with test data
- Create interactive plots through the web interface
- Write scripts to read data from devices
- Send commands from the web interface to user scripts

### Getting Started
First, create and navigate to a new project directory:
```console
$ mkdir QuickTour
$ cd QuickTour
```

### Docker Users
If you're using Docker, the directory you just created will be mounted as a volume in the container. You can work either inside the container (using `docker exec ... /bin/bash`) or outside. In the beginning, we recommend working outside the container.

# Test Data Generation
We'll use the SlowPy Python library, included with the SlowDash package, to generate test data. Create a file named `generate-testdata.py` in your project directory with the following code:
```python
import slowpy
device = slowpy.control.RandomWalkDevice()
datastore = slowpy.store.DataStore_SQLite('sqlite:///SlowStore.db', table='slowdata')
tasklet = slowpy.mesh.Tasklet()

@tasklet.loop(interval=1.0)
def loop():
    for ch in range(4):
        data = device.read(ch)
        datastore.append(data, tag=f'ch{ch:02d}')
    
if __name__ == '__main__':
    tasklet.run()
```

Details of the script are described in the [Controls](ControlsScript.html) section. For now, just copy and paste the script and use it to generate some test data. (If copy-and-paste fails, the identical source can be found at `ExampleProjects/QuickTour/01_DummyData/config/slowtask-testdata.py`. As we will see later, this script can be started from web browsers.)

If you installed SlowPy in a virtual environment (the standard installation method), activate it using either:
```console
$ slowdash-activate-venv
```
or (if `slowdash-bashrc` hasn't been sourced):
```console
$ source PATH/TO/SLOWDASH/venv/bin/activate
```

Running this script will create a SQLite database file and populate it with simulated time-series data every second:
```console
$ python generate-testdata.py
```

After letting it run for about a minute, stop the script using `Ctrl`-`c` and examine the created files:
```console
$ ls -l
-rw-r--r-- 1 sanshiro sanshiro 12288 Oct  7 07:41 SlowStore.db
-rwxr-xr-x 1 sanshiro sanshiro   376 Oct  7 07:38 generate-testdata.py
```

You can inspect the database contents using the SQLite command-line program, `sqlite3`. If this program isn't available on your system, you can skip this step and view the data through SlowDash in the next section.
```console
$ sqlite3  SlowStore.db 
SQLite version 3.46.1 2024-08-13 09:16:08
Enter ".help" for usage hints.
sqlite> .tables
slowdata
sqlite> .schema
CREATE TABLE slowdata(timestamp REAL, channel VARCHAR(100), value REAL, PRIMARY KEY(timestamp,channel));
sqlite> select * from slowdata limit 10;
1791384527.045|ch00|0.59
1791384527.074|ch01|3.537
1791384527.082|ch02|0.447
1791384527.093|ch03|-4.424
1791384528.038|ch00|0.302
1791384528.054|ch01|2.235
...
```

As shown above, the schema of the data table is:
```
slowdata(timestamp REAL, channel VARCHAR(100), value REAL, PRIMARY KEY(timestamp,channel));
```

In this example, the UNIX timestamps are used for data time. Other formats, such as DB native date time types, can be used.
For information about other supported data table formats, please refer to the [Data Binding section](DataBinding.html).

# Basic Usage

## Project Configuration
Each SlowDash project requires a configuration file named `SlowdashProject.yaml` in the project directory. This file specifies which database to read, which columns contain timestamps and data values, and other essential settings.

### Creating the Configuration File

Create `SlowdashProject.yaml` with the following content:
```yaml
slowdash_project:
  name: QuickTour
  title: SlowDash Quick Tour

  data_source:
    url: sqlite:///SlowStore.db
    time_series:
      schema: slowdata [channel] @timestamp(unix) = value
```

The `schema` entry under `time_series` describes the format of the time-series data stored in the `data_store`.
It specifies the columns and format in the following syntax:
```
TABLE [ TAG_COLUMN ] @ TIME_COLUMN (TIMESTAMP_TYPE) = VALUE_COLUMN
```

The timestamp type is specified after the time column name. Common timestamp types include:

|name | description |
|---|---|
|`unix` | UNIX timestamp (integer or real number) |
| `aware` / `with time zone` | date-time type with explicit time zones |
| `naive` / `without time zone` / `local` | date-time type with implied "local" time zone (generally not recommended) |
| `unspecified utc` | date-time type without explicit time zones but known to be in UTC |

### Verifying the Configuration

(Docker users should first enter the container using `docker exec -it CONTAINER_ID /bin/bash`.)

Test your configuration using the `slowdash config` command in the project directory:
```console
$ slowdash config --indent=2
Running in venv at /PATH/TO/SLOWDASH/venv
{
  "slowdash": {
    "version": "261008 \"Mamquam\""
  },
  "project": {
    "name": "QuickTour",
    "title": "SlowDash Quick Tour",
    "server_url": "http://slowpc:18881",
    "is_secure": false,
    "is_cgi": false,
    "is_command": true,
    "is_async": true
  },
  "data_source": {
    "SQLite": {
      "schemata": {
        "time_series": [
          "slowdata[channel]@timestamp(unix)=value"
        ],
        "object": [],
        "object_time_series": []
      }
    }
  },
  ...
```

The channels in the data-store can be listed with the `slowdash channels` command:
```console
$ slowdash channels
[
  {"name": "ch00"}, {"name": "ch01"}, {"name": "ch02"}, ...
]
```

The data values can be displayed with the `slowdash data` command:
```console
$ slowdash "data/ch00?length=10"
{
  "ch00": {
    "start": 1680223465, "length": 10, 
    "t": [0.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0], 
    "x": [5.180761, 5.92074, 5.515459, 4.883299, 5.650556, 4.284527, 3.884656, 3.223627, 2.06343]
  }
}
```

## Running the Application
### Step 1: Launch the SlowDash Server
This step starts a SlowDash server on port 18881. To stop the server, press `Ctrl`-`c`.

#### Native (directly on the host, without containers)
```console
$ slowdash --port=18881
```

#### Docker
Image from DockerHub
```console
$ docker run --rm -p 18881:18881 -v $(pwd):/project slowproj/slowdash
```
or locally created image:
```console
$ docker run --rm -p 18881:18881 -v $(pwd):/project slowdash
```

#### Docker-Compose
Create a `docker-compose.yaml` file in the project directory
```yaml
version: '3'

services:
  slowdash:
    image: slowproj/slowdash
    volumes:
      - .:/project
    ports:
      - "18881:18881"
```

Then start `docker compose`
```console
$ docker compose up
```


### Step 2: Opening a Web Browser
Launch a web browser and access `http://localhost:18881`.
```console
$ firefox http://localhost:18881
```
The browser should show the home page of the project:

<img src="fig/QuickTour-Home.png" style="width:40%">


### Step 3: Start Generating Testdata (only for this quick tour)
In order to continuously fill the data while plotting, run the test-data generator in parallel (maybe in another terminal window):
```console
$ python3 generate-testdata.py
```
The data file size is roughly 5 MB per hour. The test data file, `SlowStore.db`, can be deleted safely when SlowDash is not running.
Once the file is deleted, run `generate-testdata.py` again before starting SlowDash next time.



## Creating Plots
### Interactive Plot Building
The easiest way to get started is to explore the GUI:

- Click any channel in the "Channel List" panel to create a time-series plot
- Or click "New Plot Layout" in the "Tools" panel to start with an empty layout
- Hover over empty space to reveal the "Add New Panel" button
- Click it and select "Time-Axis Plot" to create a new plot
- Hover over any plot to access control buttons
- Click the &#x1f6e0; (wrench) icon to configure axes, styles, and add new time series

Currently, only time-series plots are available since our test database contains only time-series data.

### Saving Your Work
You can save and share your plot layouts (called SlowPlot Layouts) by clicking the &#x1f4be; (save) button in the top-right corner.
Saved layouts appear on the SlowDash home page.

### Creating Panels via URL
#### Using Configuration Files
Open a saved layout with a specific time range using a URL:
```
http://localhost:18881/slowplot.html?config=slowplot-QuickTour.json&time=2023-03-30T18:00:00&reload=0
```

#### Using Channel Specifications
Create a new layout directly through a URL by specifying channels and plot types:
```
http://localhost:18881/slowplot.html?channel=ch00;ch00/ts-histogram&length=360&reload=60&grid=2x1
```


# Reading Data from Hardware Devices
SlowDash consists of two parts, a web application (web server + browser UI) and a Python library used in user scripts.
In the previous example with test data, we used this library, called SlowPy.
The application and library work seamlessly together, but each can also operate independently.
In this section, we'll use the SlowPy library alone to read real data from a device, replacing the dummy data generator used in the previous section.

## Preparation
SlowPy is installed automatically along with SlowDash. In the standard installation, it resides inside a virtual environment (venv). Please activate this venv before starting:
```console
$ slowdash-activate-venv
```

You need to run this command every time you open a new terminal. If you're using a dedicated SlowDash machine and no other Python environments, you can add the following line to your `.bashrc` to avoid doing it manually:
```bash
source $SLOWDASH_DIR/venv/bin/activate
```

## Target Devices
Here, we'll show an example that reads DC voltage from a network-controllable digital multimeter (DMM).
Many DMMs share common command sets, and we have confirmed the following models (verified by ChatGPT, August 2025):

| Manufacturer | Model |
|---------------|--------|
| Keysight / Agilent | 34460A DMM |
| Tektronix / Keithley | DMM6500 |
| Rigol | DM3058 |
| BK Precision | 5492B DMM |

Similarly, many DC power supplies use the same command for output voltage readout. You can therefore use the same example code. The following models are confirmed (ChatGPT, August 2025):

| Manufacturer | Model |
|---------------|--------|
| Keysight / Agilent | E363x / E364x |
| Tektronix / Keithley | 2230G / 2231A |
| Rohde & Schwarz | NGA100 series |
| Rigol | DP800 / DP2000 |
| BK Precision | 9180 / 9190 |

All of these devices are controllable via Ethernet.
Before proceeding, make sure your device is powered on, connected to the network, and that you know its IP address (and port number, to be sure - see the manual).

### If No Device Is Available
According to ChatGPT, most DMMs and power supplies share a compatible command set.
If you have any network-controllable device that can report voltage, you might be able to use it here.

If you don’t have access to any physical device, SlowDash provides a built-in simulator.
You can launch it as follows:

```console
$ slowdash-activate-venv
$ cd PATH/TO/SLOWDASH/utils
$ python ./dummy-scpi.py
listening at 172.26.0.1:5025
line terminator is: x0d
type Ctrl-c to stop
```

This behaves like a real device on your local network (running on `localhost`). Press `Ctrl-C` to stop it.


## Reading Data from the Device
All of the above devices use the SCPI (Standard Commands for Programmable Instruments) text-based protocol.
The commands we'll use here are as follows:

| Action | Command | Example Response |
|---------|----------|----------------|
| Get device ID | `*IDN?` | `Keysight Technologies,34460A...` |
| Reset settings | `*RST` | (no response) |
| Read DC voltage | `MEAS:VOLT:DC?` | `3.24` |

In SlowPy, device control is represented as a logical control tree, where each node of the tree has `set(value)` and/or `get()`. For this SCPI example, the hierarchy looks like:
```
[Measurement System] → [Ethernet] → [SCPI Control] → [Command Nodes]
```

A complete SlowPy script to retrieve and print the device ID is:
```python
from slowpy.control import control_system as ctrl
print(ctrl.ethernet('172.26.0.1', 5025).scpi().command('*IDN?').get())
```
Adjust the IP address and port number as needed. With this two line code, you can verify the connection:
```console
$ slowdash-activate-venv
$ python read-my.py
Keysight Technologies,34460A...
```

Multiple calls to the connection node (`.ethernet()`) may or may not create a new connection every time, depending on the node specification and optional parameters.
A common practice is to keep the device-level node in a variable.

Example: continuously read DC voltage once per second after resetting the device.
```python
from slowpy.control import control_system as ctrl
device = ctrl.ethernet('172.26.0.1', 5025).scpi()

device.command('*RST').set()

while True:
    volt = device.command('MEAS:VOLT:DC?').get()
    print(volt)
    ctrl.sleep(1)
```
(`ctrl.sleep()` behaves like `time.sleep()`, but works better with SlowDash’s signal handling.)

## Storing Data in a Database
SlowPy also provides database-write capabilities.
The following code stores the measurements into a local SQLite database instead of printing them.
```python
from slowpy.control import control_system as ctrl
device = ctrl.ethernet('172.26.0.1', 5025).scpi()

from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///SlowStore.db', table="slowdata")

device.command('*RST').set()

while True:
    volt = device.command('MEAS:VOLT:DC?').get()
    datastore.append({'volt': volt})
    ctrl.sleep(1)
```
Running this script instead of the dummy-data generator enables SlowDash to visualize real measurements.
Stop it with `Ctrl-C` or `Ctrl-\`. (You might see messy output, but it’s harmless.)


## Integrating the Script into the SlowDash Application
Any Python script (not necessarily using SlowPy) placed in your project's `config` directory as `slowtask-XXX.py` will automatically appear in the "SlowTask" section of the SlowDash home screen, where it can be controlled via the web interface.

You can also configure it to auto-start or edit directly from the browser via entries in `SlowdashProject.yaml` (see the official documentation).

However, the previous script cannot be gracefully stopped yet. To allow start/stop control from the app, implement the callback functions defined by SlowDash, such as `_loop()` and `_run()`:

```python
from slowpy.control import control_system as ctrl
device = ctrl.ethernet('172.26.0.1', 5025).scpi()

from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///SlowStore.db', table="slowdata")

device.command('*RST').set()

def _loop():
    volt = device.command('MEAS:VOLT:DC?').get()
    datastore.append({'volt': volt})
    ctrl.sleep(1)
```

Here, `while True` is replaced by `def _loop()`.
When executed by SlowDash, `_loop()` will be repeatedly called in a managed thread.

See the "Controls Script" section of the documentation for additional callbacks such as `_initialize()` and details about threads and asynchronous execution.

To make the script runnable standalone, add:
```python
if __name__ == '__main__':
    while True:
        _loop()
```

Or, for graceful termination with `Ctrl-C`:
```python
if __name__ == '__main__':
    ctrl.stop_by_signal()
    while not ctrl.is_stop_requested():
        _loop()
```

A full working example is provided in `ExampleProjects/QuickTour/02_RealDevice`.
```console
$ cd PATH/TO/SLOWDASH/ExampleProjects/QuickTour/02_RealDevice
$ slowdash --port=18881
```

Open your browser at <http://localhost:18881> — you'll find "read-my" under SlowTask, with [start] and [stop] buttons.

You can still run the script without the SlowDash app as before:
```console
$ slowdash-activate-venv
$ python config/slowtask-read-my.py
```

## Additional Notes
For power supply devices that need voltage control:
```python
from slowpy.control import control_system as ctrl
device = ctrl.ethernet('172.26.0.1', 5025).scpi(append_opc=True)

device.command('VOLT').set(3.0)    # sends "VOLT 3.0; *OPC?"
device.command('OUTP').set('ON')   # sends "OUTP ON; *OPC?"
```

SlowPy expects every command to return a response.
If the device doesn't normally return one, append `*OPC?` to make it respond when complete.
You can apply this globally (as above) or per-command by:
```python
device.command('OUTP ON; *OPC?').set()
```

For USB or RS-232 devices, replace the Ethernet part of the control tree.
For example, using a VISA interface:
```python
from slowpy.control import control_system as ctrl
ctrl.import_control_module('VISA')    # Load VISA plugin
device = ctrl.visa('USB00::0x2A8D::0x201:MY54700218::00::INSTR').scpi()

# (rest is the same)
```

For Ethernet devices using HiSLIP, also use VISA with an address like: `TCPIP0::<IP address>::hislip0`.

## Bonus: Turning a Raspberry Pi into an SCPI Device
The SlowPy library also includes a server-side SCPI interface, allowing any Python program to act as an SCPI-controllable device, making it fully compatible with SlowDash monitoring, control, and data storage.

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

| Command | Action | Example command | Example response |
|---|---|---|---|
| `*IDN?` | Returns the device ID | `*IDN?` | `MyMemoryDevice` |
| `Volt <Value>` | Sets the value | `V 10` | (none) |
| `MEASure:Volt?` | Gets the value | `MEAS:V?` | `10` |
| `*OPC?` | Waits for command completion and returns the status | `*OPC?` | `1` |
| `SYSTem:ERRor?` | Returns an error message | `SYST:ERR?` | `invalid command: IDN?` <br>(after entering `IDN?` instead of `*IDN?`) |

SlowPy's SCPI server uses decorators to associate SCPI commands with their handlers.
When a handler argument has a type annotation, as in `set_V(value:float)` in this example, its type is checked and the value is converted when the handler is called.
Features such as SCPI command concatenation are processed before the handler is called.
Default handlers are provided for some standard commands, including `*OPC?` and `SYSTem:ERRor?`.

Configure the script to run automatically at system startup, either by registering it with systemd or adding it to `/etc/rc.local`, and the Raspberry Pi can be used as an SCPI device.
For example, to use systemd on a Raspberry Pi, create a file such as `myscpi.service` in `/etc/systemd/system` with the following contents, then run `sudo systemctl enable myscpi.service`. 
(This example runs the script in the SlowDash virtual environment.)

```ini
[Unit]
Description=My SCPI Server

[Service]
Type=simple
User=MY_USER_NAME
WorkingDirectory=/PATH/TO/PROJECT
ExecStart=/PATH/TO/SLOWDASH/venv/bin/python /PATH/TO/PROJECT/myscpi.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

This is convenient not only for using the attached hardware through GPIB/I2C/SPI, but also for integrating USB devices (even with a vendor-provided library) as Ethernet-SCPI devices.


# Control from the Web GUI
In the two examples above, we first used SlowDash as a data browser and then used the SlowPy library to retrieve data, but they were separate pieces. Here, we will integrate them so that you can control a device from the browser, acquire data, and send it back to the browser either through the database or by direct streaming for display.

We will proceed in the following four steps:

1. Create an input form with buttons in the browser and call Python script functions on button clicks
2. Add input elements in the browser and pass their values as function call arguments
3. Send data directly from Python code to the browser and change control panel display based on the current state
4. Build a histogram in Python code and send it directly to the browser for real-time display

Eventually, we will create a SlowDash layout like this:

<img src="fig/QuickTour-DeviceControlFull.png" style="width:70%;box-shadow:0px 0px 15px -5px rgba(0,0,0,0.7);">


## Calling Functions from the Browser
(The code used here is in `ExampleProjects/QuickTour/03_RealDeviceControl/01_StartStop`.)

On the SlowDash browser, you can display user-created HTML forms. 
If you place input elements such as `<input type="number">` there and create buttons with `<input type="submit">`, clicking a button can call a function in your Python script.
The function name to call is specified with the button's `name` attribute.

First, we add start/stop control to the device readout script created in the previous example. 
This time, save it as `slowtask-testdaq.py` under the `config` directory.
```python
from dataclasses import dataclass

@dataclass
class RunStatus:
    running: bool = False
run_status = RunStatus()
    

from slowpy.control import control_system as ctrl
device = ctrl.ethernet('192.168.1.34', 5025).scpi()

from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///SlowStore.db', table="slowdata")


def _loop():
    if run_status.running:
        try:
            volt = float(device.command('MEAS:VOLT:DC?').get() or 'nan')
            datastore.append({'volt': volt})
        except Exception as e:
            print(f'ERROR: {e}')
        
    ctrl.sleep(1)


def start():
    run_status.running = True
    
    
def stop():
    run_status.running = False
```
The `run_status` data class manages the current run state. 
Later we will add more state variables, but for now it only has the `running` flag that indicates whether acquisition is active. 
The main loop checks this variable to decide whether to read data from the device. 
We also define `start()` and `stop()` so this flag can be set externally.
We also added error handling to make the script more practical in realistic situations.

Create a form to call these `start()` and `stop()` functions from the browser, save it as `html-testdaq.html`, and place it under `config`. 
The filename must start with `html-` and have the `.html` extension.

```html
<form>
  <input type="submit" name="testdaq.start()" value="Start">
  <input type="submit" name="testdaq.stop()" value="Stop">
</form>    
```

Here, we simply create two buttons corresponding to the two functions. 
In each button's `name` attribute, specify which function in which file should be called when the button is clicked. 
The `name` format is the script filename (the `XXX` part of `slowtask-XXX.py`) and the function name in that script.

After creating and placing these files under `config`, restart slowdash. 
In the SlowTask section at the lower left of the home screen, you should see a task called `testdaq`; click `start` there to start the script.
If manually starting every time is inconvenient, add the following to `SlowdashProject.yaml` to auto-start the script when slowdash starts.

```yaml
slowdash_project:
  name: QuickTour
  title: SlowDash Quick Tour
  
  data_source:
    url: sqlite:///SlowStore.db
    time_series:
      schema: slowdata [channel] @timestamp(unix) = value

  task:
    name: testdaq
    auto_load: true
```

Once the script is running, create a new layout via New Plot Layout, choose HTML Form in Add New Panel, and set the HTML file to `testdaq`. 
This should place a form with two buttons in the layout.
By clicking the buttons, you can start/stop data acquisition, and once data is saved, you can create a time-series plot using the same steps as before.
(No data exists before the first Start, so you cannot create the plot yet. After pressing Start, click the Channel List refresh button, or save the layout and reload the whole page.)

## Passing Parameters from the Browser
(The code used here is in `ExampleProjects/QuickTour/03_RealDeviceControl/02_Params`.)

Next, we add input elements to the form so their values are passed to the script as function arguments.
Here, we add an option to specify run duration so the run can automatically stop after the specified time.
The new variables are a real-valued run length `run_length` and a boolean `auto_stop` indicating whether auto-stop is enabled.
On the HTML side, we only add input elements. 
A checkbox is used for the boolean.

```html
<form>
  <input type="checkbox" name="auto_stop">Stop After:
  <input type="number" name="run_length" value="10">
  <br>
  <input type="submit" name="testdaq.start()" value="Start">
  <input type="submit" name="testdaq.stop()" value="Stop">
</form>    
```

The `name` attribute of each `<input>` element becomes the parameter name on the script side.
In the script, add parameters to the function called when a button is pressed.
To support auto-stop and related behavior, we add several required fields to `RunStatus`.

```python
@dataclass
class RunStatus:
    auto_stop: bool = False
    run_length: float = 0
    start_time: float = 0
    running: bool = False
run_status = RunStatus()


def _loop():
    if run_status.running:
        try:
            volt = float(device.command('MEAS:VOLT:DC?').get() or 'nan')
            datastore.append({'volt': volt})
        except Exception as e:
            print(f'ERROR: {e}')
            
        if run_status.auto_stop:
            now = time.time()
            if now - run_status.start_time >= run_status.run_length:
                run_status.running = False
                        
    ctrl.sleep(1)


def start(auto_stop:bool, run_length:float):
    run_status.auto_stop = auto_stop
    run_status.run_length = run_length

    run_status.start_time = time.time()
    run_status.running = True
    
    
def stop():
    run_status.running = False
```

As in this example, if you add type annotations to function parameters, type checking and conversion are automatically performed before the function call. 
If the types do not match, an error is returned to the browser before the function is called.

## Sending Status Information from the Script to the Browser
(The code used here is in `ExampleProjects/QuickTour/03_RealDeviceControl/03_Status`.)

On the browser side, it is convenient to display the current status and enable/disable buttons such as Start and Stop accordingly.
To do this, we send data directly from the script to the browser so the HTML form can be controlled dynamically.

To send data directly from the script to the browser without going through the database, use `ctrl.stream(name:str, value)` on the `ControlSystem` instance `ctrl` (`await ctrl.aio_stream(name, value)` for async).
For `value`, you can pass numbers and strings, as well as dataclasses and dicts.
Numbers and strings are treated as scalar data, while dataclasses and dicts are treated as Tree-type data.

In the example below, Run Status is sent every second.

```python
def _loop():
    if run_status.running:
        try:
            volt = float(device.command('MEAS:VOLT:DC?').get() or 'nan')
            datastore.append({'volt': volt})
        except Exception as e:
            print(f'ERROR: {e}')
            
        if run_status.auto_stop:
            now = time.time()
            if now - run_status.start_time >= run_status.run_length:
                run_status.running = False

    ctrl.stream('run_status', run_status)
    ctrl.sleep(1)
```
Because Run Status is a dataclass, the browser can display it directly as Tree data.
Restart SlowDash, or stop and start this script again from the SlowTask panel, and `run_status` will appear in Data Channels as `current tree` data.
In the layout containing the input form created earlier, you can add it via Add a New Panel -> Tree -> `run_status`.

In HTML added as an HTML form panel in a layout, SlowDash provides an extension where `<input>` elements can use the `sd-enabled` attribute, allowing the `enabled` state to be dynamically switched based on a data value.
Here the data value for `sd-enabled` must be boolean.
If the data value is not boolean, use SlowDash Data Transform to convert it.
In this example, `run_status` is a Tree type, so we extract the `running` field and apply logical inversion (`invert()`) as needed.
Data Transform is still in an experimental stage and may change in the future, but the basic features used here are likely to remain.

```html
<form>
  <input type="checkbox" name="auto_stop">Stop After:
  <input type="number" name="run_length" value="10">
  <br>
  <input type="submit" name="testdaq.start()" value="Start" sd-enabled="run_status['running']->invert()">
  <input type="submit" name="testdaq.stop()" value="Stop" sd-enabled="run_status['running']">
</form>    
```
Other frequently used Data Transforms for `sd-enabled` include `->gt(thresh)` / `->lt(thresh)` for numeric comparisons and `->match(pattern)` for string matching.

## Run Analysis in the Script and Send Results to Browsers
(The code used here is in `ExampleProjects/QuickTour/03_RealDeviceControl/04_Analysis`.)

The SlowPy library includes lightweight analysis data objects such as histograms, and histograms built with them can also be streamed to the browser. 
(You can also save them to the database as usual.)
Below is an example that reads data every second, records it in the database, updates a histogram, and sends it to the browser in real time.

```python
from slowpy import Histogram
histogram = Histogram(nbins=20, range_min=-10, range_max=10)


def _loop():
    if run_status.running:
        try:
            volt = float(device.command('MEAS:VOLT:DC?').get() or 'nan')
            datastore.append({'volt': volt})
            histogram.fill(volt)
        except Exception as e:
            print(f'ERROR: {e}')
            
        if run_status.auto_stop:
            now = time.time()
            if now - run_status.start_time >= run_status.run_length:
                run_status.running = False

    ctrl.stream('run_status', run_status)
    ctrl.stream('hist01', histogram)
    ctrl.sleep(1)
```

Restart SlowDash, or stop and start this script again from the SlowTask panel, and `hist01` will appear in Data Channels as `current histogram` data.
You can add it to the layout via Add a New Panel -> XY Plot -> Histogram Object -> `hist01`.



# Mesh and Tasklet

Multiple SlowTasks can communicate with each other and can also be distributed across multiple computers.
SlowMesh provides the communication infrastructure, while Tasklet provides the interface for connecting to SlowMesh and managing task lifecycles, including startup and shutdown.
A SlowTask script equipped with a Tasklet can therefore cooperate with other tasks through SlowMesh.
In this section, we will split the SlowTask script from the previous section into separate readout, analysis, and storage components, run them as multiple processes, and coordinate them through SlowMesh.

## Converting a SlowTask Script to Use Tasklet

### Lifecycle Callbacks

In the previous section, callbacks such as `_initialize()` and `start()` were used implicitly.
Tasklet uses Python decorators to declare callbacks explicitly and provides additional controls.

Callbacks can be either regular Python functions or async functions.
Using async callbacks allows asynchronous operations with `await` inside the function.
This is more efficient in many situations, so the examples below use async functions.
Even if you are unfamiliar with async functions, you can write their bodies just like regular functions until you need asynchronous operations.
(However, do not use `time.sleep()` / `ctrl.sleep()`, as explained below.)

With Tasklet, the `_initialize()` callback that was invoked implicitly in the previous examples is declared as follows:

```python
from slowpy.mesh import Tasklet
tasklet = Tasklet()

@tasklet.initialize()
async def my_init():
    ...
```

The function can have any name; `my_init()` is just an example.
You can also keep the previous name, `_initialize()`.
The function does not have to be async.
You can define multiple `@tasklet.initialize()` callbacks.

You can also receive parameters from the SlowDash configuration file (`SlowdashProject.yaml`).

```python
@tasklet.initialize()
async def my_init(parameters:dict):
    db_url = parameters.get('DB_URL')
    ...
```

The repeatedly invoked `_loop()` callback becomes:

```python
@tasklet.loop(interval=1)
async def my_loop():
    ...
```

The `interval` argument of the `loop()` decorator specifies how often the function is called.
There is therefore no need to sleep inside the function.
You can add the `ticks` argument to perform some operations less frequently within the loop.

```python
@tasklet.loop(interval=1, ticks=10)
async def my_loop(ticks):
    # Called every second.
    # For example, read data and fill a histogram.
    if ticks:
        # Executed every 10 seconds (every 10 loop calls).
        # For example, save the histogram.
        ...
```

You can also specify multiple tick counters.

```python
@tasklet.loop(interval=0.1, ticks={'monitor':10, 'store':100})
async def my_loop(ticks):
    # Called every 0.1 seconds.
    if ticks.monitor:
        # Executed every second (every 10 loop calls).
        ...
    if ticks.store:
        # Executed every 10 seconds (every 100 loop calls).
        ...
```

Using intervals and ticks should eliminate most needs for explicit sleeps.
SlowTask is primarily a single-threaded asynchronous system, so a blocking operation such as `time.sleep()` and `ctrl.sleep()` in a user script stops the entire system.
If you do need to sleep, use the asynchronous `await ctrl.aio_sleep()` (or `await asyncio.sleep()`) instead.

Use `@tasklet.once(delay=0)` in place of `_run()`:

```python
@tasklet.once()
async def my_run():
    ...
```

Other decorators include `@tasklet.schedule("08:00,16:00")` and `@tasklet.finalize()`.

Once a script uses Tasklet, implicit callbacks such as `_initialize()` are no longer called.
See the Mesh documentation for details.

### Exporting Functions

To make a Python function in a SlowTask script callable from the browser or other clients, export it to Mesh.

```python
@tasklet.mesh.export()
async def start(auto_stop:bool, run_length:float):
    ...
```

The function does not have to be async.
Without Tasklet, all functions were exported implicitly.
With Tasklet, functions must be exported explicitly.

### Content Generation Functions

The `@tasklet.content("config/XXX")` decorator allows a script to dynamically generate content for the project's `config` directory.
The following example generates the contents of the `config/html-testdaq.html` file from the previous section within the task script.

```python
@tasklet.content('config/html-testdaq.html')
async def html():
    return '''
      <form>
        <input type="checkbox" name="auto_stop">Stop After:
        <input type="number" name="run_length" value="10">
        ...
      </form>
    '''
```

This makes it easier to keep the task script and its HTML consistent.

In an HTML panel, selecting `On Update: Reload HTML` calls this function on every page update.
You can use this to generate dynamic HTML containing data.
For example, the following function monitors disk usage and generates an HTML table.

```python
import shutil, datetime

@tasklet.content('config/html-disk_usage.html')
async def html_disk_usage():
    total, used, free = tuple((int(x*1e-8)/10.0) for x in shutil.disk_usage('.'))
    used_percent = int(100 * used/total) if total > 0 else 100
    return f'''
        <span style="font-size:300%">{used_percent}</span>
        <span style="font-size:250%">% used</span>
        <p>
        <table>
          <tr><td>Total</td><td>{total} GB</td></tr>
          <tr><td>Used</td><td>{used} GB</td></tr>
          <tr><td>Free</td><td>{free} GB</td></tr>
        </table>
        <p>
        As of {str(datetime.datetime.now())}
    '''
```

SlowDash simply calls this function periodically.
Its body is ordinary Python code, so you can also use a template engine such as Jinja.

### Form Synchronization

Giving a `<form>` element a name in an HTML panel causes its input values to be sent to the server whenever they change (on a `change` event).
The displayed values are then immediately synchronized across browsers viewing the same page.
When the server shuts down, the values are saved to a file in the project directory (`registry-pubsub-form.json`) and used as the initial form values at the next startup.

```html
<form name="testdaq">
  <input type="checkbox" name="auto_stop">Stop After:
  <input type="number" name="run_length" value="10">
  ...
</form>
```

For reference, `registry-pubsub-form.json` contains entries like this:

```json
{
  "testdaq.run_length": {
    "value": {
      "sender_id": "a21586ac-fa5e1120-5c99e150-9d906172",
      "form": "testdaq",
      "element": "run_length",
      "value": 10
    },
    "revision": 1,
    "updated": 1791993688.100811
  }
}
```

### Example

An example that rewrites the SlowTask script from `QuickTour/03_RealDeviceControl/04_Analysis` using Tasklet is available in `QuickTour/04_Mesh/01_Tasklet`.
Its behavior is unchanged.

The changes are:

- Import `Tasklet` and create a `tasklet` instance.
- Explicitly declare the loop callback with `@tasklet.loop(interval=1.0)` and remove the `time.sleep(1.0)` call inside it.
- Explicitly export the browser-callable `start()` and `stop()` functions with `@tasklet.mesh.export()`.
- Remove `config/html-testdaq.html` and generate its contents with a function decorated with `@tasklet.content("config/html-testdaq.html")`.
- Give the HTML form a name to enable synchronization across browsers and persistence of input values.

Here is the complete updated SlowTask script (`config/slowtask-testdaq.py`).

```python
### The first part is unchanged.

import time
from dataclasses import dataclass

@dataclass
class RunStatus:
    auto_stop: bool = False
    run_length: float = 0
    start_time: float = 0
    running: bool = False
run_status = RunStatus()


from slowpy.control import control_system as ctrl
device = ctrl.ethernet('192.168.1.34', 5025).scpi()

from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///SlowStore.db', table="slowdata")

from slowpy import Histogram
histogram = Histogram(nbins=20, range_min=-10, range_max=10)


### The code below has been converted to use Tasklet.

from slowpy.mesh import Tasklet
tasklet = Tasklet()


@tasklet.loop(interval=1)
async def loop():
    if run_status.running:
        try:
            volt = float(device.command('MEAS:VOLT:DC?').get() or 'nan')
            datastore.append({'volt': volt})
            histogram.fill(volt)
        except Exception as e:
            print(f'ERROR: {e}')

        if run_status.auto_stop:
            now = time.time()
            if now - run_status.start_time >= run_status.run_length:
                run_status.running = False

    ctrl.stream('run_status', run_status)
    ctrl.stream('hist01', histogram)


@tasklet.mesh.export()
async def start(auto_stop:bool, run_length:float):
    run_status.auto_stop = auto_stop
    run_status.run_length = run_length

    run_status.start_time = time.time()
    run_status.running = True


@tasklet.mesh.export()
async def stop():
    run_status.running = False


@tasklet.content('config/html-testdaq.html')
async def html():
    return '''
      <form name="testdaq">
        <input type="checkbox" name="auto_stop">Stop After:
        <input type="number" name="run_length" value="10">
        <br>
        <input type="submit" name="testdaq.start()" value="Start" sd-enabled="run_status['running']->invert()">
        <input type="submit" name="testdaq.stop()" value="Stop" sd-enabled="run_status['running']">
      </form>
    '''
```

## Separating and Coordinating Tasks with Mesh

### PubSub Network Communication

Mesh provides the communication infrastructure for coordinating SlowTasks, with the following features:

- Message exchange through Publish/Subscribe (PubSub)
- Remote Procedure Calls (RPC) to exported functions
- Sharing named values across tasks through a key-value store (registry), with persistence across sessions

With PubSub, a sender publishes what it has without knowing who will receive it.
Receivers subscribe to the topics they need without knowing who sent the messages.
This differs significantly from RPC, which requires knowledge of the other component's behavior and interface, and greatly reduces dependencies between components.

SlowDash makes extensive use of PubSub for distributed processing.
Tasks publish acquired data to the mesh for other components to process, publish requests for other components to act on, subscribe to relevant topics, perform their own responsibilities on received data, and publish any results back to the mesh.

Messages have topic names such as data, command, or alarm, and receivers specify which topics to subscribe to.
In this communication model, the shared agreements are the topic names and the contents and structure (schema) of the messages exchanged on each topic.

Topics can have a dot-separated hierarchy, such as `data.store.HV.ch01.setpoint`.
Receivers can use patterns within this hierarchy, such as `data.store.>` (everything under `data.store`) or `data.*.HV.>`.

<img src="fig/SlowMeshConcept.png" width="40%">

To publish data to the mesh:

```python
from slowpy.mesh import DataPacket

@tasklet.loop(interval=...)
async def read_data():
    volt = float(device.command('MEAS:VOLT:DC?').get() or 'nan')

    topic = 'data.store'
    await tasklet.mesh.aio_publish(topic, DataPacket({'volt': volt}))
```

This publishes a data message on the `data.store` topic.
`DataPacket` converts the data to the message schema defined for that topic.
Its constructor takes the same parameters as `DataStore.append()`, so code that writes directly to a DataStore can be reused with very few changes.

The `aio_publish()` function is async and must be called with `await`.
The function containing that call (`read_data()` in this example) must therefore also be async.
For a regular function, use `publish()` instead of `aio_publish()`.

```python
from slowpy.mesh import DataPacket

@tasklet.loop(interval=...)
def read_data():
    volt = float(device.command('MEAS:VOLT:DC?').get() or 'nan')

    topic = 'data.store'
    tasklet.mesh.publish(topic, DataPacket({'volt': volt}))
```

To receive data from topics beginning with `data.`, including `data.store`:

```python
@tasklet.mesh.on('data.>')
async def handle_data(data: DataPacket):
    t = data.timestamp
    for ch, value in data.values.items():
        ...
```

Here, `DataPacket` is used again to decode the received message.

### Example

We will now split the previous example into three task processes that communicate through the mesh.

- `slowtask-read.py`: Reads data from the SCPI device and publishes it to the mesh.
- `slowtask-store.py`: Receives data from the mesh and saves it to the database.
- `slowtask-histogram.py`: Receives data from the mesh, fills a histogram, and publishes the histogram back to the mesh.

The files for this example are in `ExampleProjects/QuickTour/04_Mesh/02_Mesh`.
As before, run `slowdash --port=18881` in the project directory.
The behavior is unchanged.

Stopping the server with `Ctrl-C` also automatically stops all task processes.
Task processes launched by the server also terminate automatically if the server crashes unexpectedly or is forcibly terminated with `kill -KILL`.
(This may not work on Windows without WSL.)

#### `slowtask-read.py`

The readout task is mostly unchanged from the previous `slowtask-testdaq.py`.
It publishes data to the mesh instead of writing to the datastore, and no longer fills the histogram itself.

```python
@tasklet.loop(interval=1)
async def loop():
    if run_status.running:
        try:
            volt = float(device.command('MEAS:VOLT:DC?').get() or 'nan')
            await tasklet.mesh.aio_publish('data.store', slowpy.mesh.DataPacket({'volt': volt}))   # Publish the data.
        except Exception as e:
            print(f'ERROR: {e}')

        if run_status.auto_stop:
            now = time.time()
            if now - run_status.start_time >= run_status.run_length:
                run_status.running = False

    ctrl.stream('run_status', run_status)

@tasklet.mesh.export()
async def start(auto_stop:bool, run_length:float):
    run_status.auto_stop = auto_stop
    run_status.run_length = run_length

    await tasklet.mesh.aio_publish('mydaq.control.start', {})   # Announce the start of a run.

    run_status.start_time = time.time()
    run_status.running = True

@tasklet.mesh.export()
async def stop():
    run_status.running = False
```

Inside `start()`, a message is sent on the `mydaq.control.start` topic to notify other tasks that a run is starting.
This is used below to clear the histogram, for example.

Mesh topic names are reserved across SlowDash, but names beginning with `my` or an uppercase letter (such as `KamLAND.ctrl`) are available for users to define freely.

#### `slowtask-store.py`

This task is dedicated to database storage.
It receives data from the mesh's `data.store` topic and writes it to the database.

```python
import slowpy
tasklet = slowpy.mesh.Tasklet()

datastore = slowpy.store.DataStore_SQLite('sqlite:///SlowStore.db', table="slowdata")

@tasklet.mesh.on('data.store.>')
async def store(data: slowpy.mesh.DataPacket):
    datastore.append(data.values)
```

#### `slowtask-histogram.py`

This task receives data from the mesh's `data.store` topic and fills a histogram with values from the `volt` channel.
The histogram is published to the `data.stream` topic once per second.

The `ctrl.stream(name, value)` method used earlier internally uses `aio_publish('data.stream', DataPacket({name:value}))` to publish the data to the `data.stream` topic.

```python
import slowpy

tasklet = slowpy.mesh.Tasklet()
histogram = slowpy.Histogram(nbins=20, range_min=-10, range_max=10)

@tasklet.mesh.on('data.store.>')
async def process_data(data: slowpy.mesh.DataPacket):
    for ch, value in data.values.items():
        if ch == 'volt':
            histogram.fill(value)

@tasklet.loop(interval=1)
async def stream_result():
    await tasklet.mesh.aio_publish('data.stream', slowpy.mesh.DataPacket(histogram, tag='hist01'))

@tasklet.mesh.on('mydaq.control.start')   # The readout task announces the start of a run.
async def clear():
    histogram.clear()
```

The histogram is cleared when the `mydaq.control.start` message is published by `slowtask-read.py` at the start of a run.
Publishing the histogram from a loop callback keeps its publication rate independent of the incoming data rate.
