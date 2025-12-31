Dripline with SlowDash
======================

SlowDash provides an interactive data visualization and control panel front-end GUI that integrates with back-end user Python scripts (SlowTask).
The SlowDash Python library, SlowPy, is designed for use within SlowTask scripts and offers convenient methods to interact with measurement devices and systems, including Dripline.

This document explains how to integrate a Dripline system with SlowDash, using a Dripline system example from the Dripline First-Mesh tutorial.
It provides a series of step-by-step examples, ranging from basic visualization to fully functional Dripline services.

- Example 1: Adding SlowDash data visualization to Dripline
- Example 2: Sending SET/GET/CMD commands to Dripline endpoints
- Example 3: Controlling Dripline endpoints with the SlowDash Python library (SlowPy)
- Example 4: Sending (sensor) data values to the Dripline Mesh / Manual data entry
- Example 5: Receiving (sensor) data values from other Dripline endpoints
- Example 6: Handling SET/GET/CMD commands from other Dripline components

These examples make extensive use of the chain-of-control-nodes structure in the SlowPy library and the Dashboard–Script interconnection.
For details on these features, refer to the “Control Script” section of the SlowDash documentation.

## TL;DR
This section provides a concise summary for quick reference.
Detailed explanations are given in the following sections.

#### Connecting to the Dripline Mesh
```python
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')
```

To use the asynchronous version, import `AsyncDripline` instead of `Dripline` and use `async_dripline()`:
```python
ctrl.import_control_module('AsyncDripline')
dripline = ctrl.async_dripline('amqp://dripline:dripline@rabbit-broker')
```
Then use `aio_set()` and `aio_get()` instead of `set()` and `get()`.

#### Setting a value on an endpoint
```python
dripline.endpoint(name).set(value)
```
```python
await dripline.endpoint(name).aio_set(value)
```

#### Getting a raw value from an endpoint
```python
value = dripline.endpoint(name).value_raw().get()
```
```python
value = await dripline.endpoint(name).value_raw().aio_get()
```

#### Setting a value with ramping (or other SlowPy logic)
```python
dripline.endpoint(name).ramping(changes_per_sec).set(value)
```
```python
await dripline.endpoint(name).ramping(changes_per_sec).aio_set(value)
```

#### Checking or controlling ramping status
```python
status = dripline.endpoint(name).ramping().status().get()
dripline.endpoint(name).ramping().status().set(0)  # stop ramping
```
```python
status = await dripline.endpoint(name).ramping().status().aio_get()
await dripline.endpoint(name).ramping().status().aio_set(0)  # stop ramping
```

#### Sending data values (typically stored together with other sensor values)
```python
dripline.sensor_value_alert(endpoint_name).set(value)
```
```python
await dripline.sensor_value_alert(endpoint_name).aio_set(value)
```
where `value` may be:
- a scalar for `value_raw`
- a tuple of two scalars for `value_raw` and `value_cal`
- a dictionary (used as-is)

#### Receiving data values  
Available only in the async version:
```python
message = await dripline.sensor_value_queue().aio_get()
if message is not None and message.body is not None:
    endpoint_name = message.parameters['routing_key'].split('.')[1]
    timestamp = message.headers.get('timestamp', None)
    value_raw = message.body.get('value_raw', None)
```
Empty replies may occur when SlowDash shuts down or when the broker closes the connection.

#### Handling SET/GET/CMD requests (and sending heartbeats)  
Available only in the async version:
```python
await dripline.service(handler).aio_start()
```
where `handler` implements an `on_set(message)` method (either async or not):
```python
class MyHandler:
    async def on_set(self, message):
        print(message.body)                                   # parsed JSON data
        return {'reply': 'Your message has been received'}     # data body to return
handler = MyHandler()
```

## Example 01: Plotting
### Objectives
This example demonstrates how to add SlowDash data visualization to the Dripline First-Mesh Walkthrough.

| Screenshot |
|------------|
|<img src="FirstMeshPlotting.png" width="100%">|

### Running the Example
The `01_Plotting` directory contains the complete set of files. Run the following command:
```bash
cd 01_Plotting
docker compose up
```
Wait for RabbitMQ to become ready (about 30 seconds). Then open a web browser and navigate to `http://localhost:18881`.
On the SlowDash home page, the Data Channels panel (top left) lists data channels (endpoints). Clicking a channel name creates an initial layout with a plot panel. You can modify or add panels to the layout.

To stop, press `Ctrl+C` in the terminal. Run `docker compose down` before running another example.

### Setup Procedure for Your Project
1. Add a SlowDash container in your Docker Compose file.
2. Optionally, create a SlowDash working directory (`slowdash.d` in this example).
3. Write a SlowDash configuration file.

#### Step 1
Append the following block to your `docker-compose.yaml`:
```yaml
  slowdash:
    image: slowproj/slowdash
    ports:
      - "18881:18881"
    volumes:
      - ./slowdash.d:/project
    depends_on:
      rabbit-broker:
        condition: service_healthy
      postgres:
        condition: service_healthy
```

#### Step 2
```bash
mkdir slowdash.d
cd slowdash.d
```

#### Step 3
Create a `SlowdashProject.yaml` file with the following content:
```yaml
slowdash_project:
  name: DriplineFirstMesh
  title: Dripline First-Mesh Walkthrough

  data_source:
    url: postgresql://postgres:postgres@postgres:5432/sensor_data
    parameters:
      time_series:
        schema: numeric_data [sensor_name] @timestamp(with timezone) = value_raw(default), value_cal
```

### How It Works
For data visualization, SlowDash requires at least the data source location (database URL) and the data format (“schema”).
The `data_source` section in the SlowDash configuration file defines these.

The schema specifies table and column names and describes which columns are for timestamps, endpoint names, and data values. For example:
```yaml
      time_series:
        schema: numeric_data [sensor_name] @timestamp(with timezone) = value_raw(default), value_cal
```
corresponds to the SQL table:
```sql
CREATE TABLE numeric_data (
  sensor_name TEXT NOT NULL,
  "timestamp" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  value_raw DOUBLE PRECISION NOT NULL,
  value_cal DOUBLE PRECISION
);
```
which is defined in the Dripline PostgreSQL configuration (First-Mesh Walkthrough).

## Example 02: Controlling Endpoints
### Objectives
This example demonstrates:
- How to link user Python code to the SlowDash GUI
- How to send SET/GET/CMD commands to Dripline endpoints from user Python code (SlowTask)

| Screenshot |
|------------|
|<img src="FirstMeshControl.png" width="100%">|

### Running the Example
The `02_Control` directory contains the complete set of files. Run:
```bash
cd 02_Control
docker compose up
```
Wait for RabbitMQ to become ready (about 30 seconds). Then open a web browser and go to `http://localhost:18881`.
On the SlowDash home page, the “SlowDash, SlowPlot, SlowCruise” panel (top right) has an icon labeled peaches-control.
Click it to open the layout shown in the screenshot above.

To stop, press `Ctrl+C` in the terminal. Run `docker compose down` before starting another example.

### Setup Procedure for Your Project
In addition to the previous example:

1. Create a user Python script (SlowTask) that receives user input and controls the endpoints.
2. Create an HTML form for the control panel.
3. Enable the Python script in the SlowDash configuration file.

#### Step 1
Create a `slowtask-control_peaches.py` file under your `YOUR/SLOWDASH/PROJECT/config` directory:
```python
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

print('hello from control_peaches.py')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')
peaches = dripline.endpoint('peaches')

def set_peaches(value: float):
    print(f'setting peaches to {value}')
    peaches.set(value)
```

#### Step 2
Create a `html-peaches-control.html` file under `config`:
```html
<form>
  value: <input type="number" name="value" style="width:8em" step="any" value="0">
  <input type="submit" name="control_peaches.set_peaches()" value="set" style="font-size:130%">
</form>    
```

#### Step 3
Add the following block to your `SlowdashProject.yaml`:
```yaml
  task:
    name: control_peaches
    auto_load: true

  system:
    our_security_is_perfect: true    # enables the Python script editor on the SlowDash web interface
```

### How It Works
This example demonstrates integration between SlowDash’s web interface and Dripline’s control system via SlowTask scripts.
Key features include:

- Setting a value on a Dripline endpoint using: `dripline.endpoint(name).set(value)`
- Binding a standard Python function (e.g., `set_peaches()`) to an HTML button whose parameters are taken from HTML form inputs.
- Output from `print()` in your script appears directly in the browser.

**SlowTask Script (`slowtask-control_peaches.py`)**
- Imports the Dripline control module through SlowPy’s dynamic plugin loader.
- Establishes a connection to the RabbitMQ broker.
- Creates a reference to the `peaches` endpoint.
- Exposes `set_peaches()` automatically to the web interface through SlowDash’s task system.

**HTML Form (`html-peaches-control.html`)**
- Provides a web form with a numeric input field.
- The submit button triggers the `control_peaches.set_peaches()` function.
- Form input values are bound by parameter names; mismatches raise an error without executing the function.

**Configuration (`SlowdashProject.yaml`)**
- The `task` section defines the SlowTask and loads it automatically.
- `system.our_security_is_perfect: true` enables the in-browser script editor; remove this if there are any security concerns.

## Example 03: Controlling Endpoints with SlowPy Logic
### Objectives
Building on the previous example, this example shows:
- How to use control logic (such as ramping) in the SlowDash Python library (SlowPy)
- How to send data directly from user Python code to the SlowDash GUI

| Screenshot |
|------------|
|<img src="FirstMeshControlSlowpy.png" width="100%">|

### Running the Example
The `03_ControlSlowpy` directory contains the complete set of files. Run:
```bash
cd 03_ControlSlowpy
docker compose up
```
Wait for RabbitMQ to become ready (about 30 seconds). Then open a web browser and navigate to `http://localhost:18881`.

To stop, press `Ctrl+C` in the terminal. Run `docker compose down` before running another example.
On the SlowDash home page, the “SlowDash, SlowPlot, SlowCruise” panel (top right) has an icon labeled peaches-control.
Click it to open the layout shown in the screenshot above.

### Setup Procedure for Your Project
In addition to the steps in the previous example:
1. Modify the user Python script (SlowTask) to add more features.
2. Modify the HTML form to provide additional controls.

#### Step 1
Replace the `slowtask-control_peaches.py` file from the previous example with the following content:
```python
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

print('hello from control_peaches.py')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')
peaches = dripline.endpoint('peaches').value_raw()

def set_peaches(target: float, ramping_rate: float):
    print(f'setting peaches to {target}, with ramping at {ramping_rate}')
    peaches.ramping(ramping_rate).set(target)
    
def abort_ramping():
    peaches.ramping().status().set(0)
    
ctrl.export(peaches.ramping(), name='ramping_target')
ctrl.export(peaches.ramping().status(), name='ramping_status')
```

#### Step 2
Replace the `html-peaches-control.html` file with the following:
```html
<form style="font-size:100%">
  <table>
    <tr>
      <td>Target</td><td>
        <input type="number" name="target" style="width:8em" step="any" value="0">
      </td><td></td>
    </tr><tr>
      <td>Ramping</td><td>
        <input type="number" name="ramping_rate" style="width:8em" step="any" value="0"> /s
      </td><td></td>
    </tr><tr>
    <td></td><td></td><td style="font-size:150%">
        <input type="submit" name="control_peaches.set_peaches()" value="set">
        <input type="submit" name="async control_peaches.abort_ramping()" value="abort">
      </td>
    </tr>
  </table>
</form>    
```

### How It Works
This example extends the basic control functionality by introducing SlowPy control logic and a direct data connection from user scripts to the web browser without going through the database.
In this example, ramping control is added to endpoint value setting. Key features include:

- SlowPy builds a chain of control nodes. Appending a ramping node to a control node (endpoint) with `.ramping()` creates a new node with attached ramping logic; setting a value via `endpoint(name).ramping(speed).set(value)` starts a sequence of `endpoint(name).set(ramping_value)` calls.
- The chain can be further extended. For example, `endpoint(name).ramping(speed).status().set(0)` adds a new function (stop ramping) to the ramping node.
- Values in user scripts can be directly exported to browsers. On the browser side, exported values appear like values stored in the database (except that historical values are not persisted).

**SlowTask Script (`slowtask-control_peaches.py`)**
- `peaches.ramping(rate)` attaches a SlowPy ramping logic node to the `peaches` node.
- `.status()` attaches a status node to the ramping node.
- Setting a value (`set(value)`) on the ramping node starts a ramping sequence to its attached node (`peaches`).
- Setting `0` on the status node stops ramping of its attached node (`peaches.ramping()`).
- SlowPy node values can be exported to external systems (e.g., web browsers) using `ctrl.export()`.

## Example 04: Writing (Sensor) Data Values / Manual Entry
### Objectives
This example shows how to send Dripline alert messages (such as sensor value alerts) and demonstrates manual data entry from the SlowDash GUI.

| Screenshot |
|------------|
|<img src="FirstMeshManualEntry.png" width="100%">|

### Running the Example
The `04_ManualEntry` directory contains the complete set of files. Run:
```bash
cd 04_ManualEntry
docker compose up
```
Wait for RabbitMQ to become ready (about 30 seconds). Then open a web browser and navigate to `http://localhost:18881`.
On the SlowDash home page, the “SlowDash, SlowPlot, SlowCruise” panel (top right) has an icon labeled manual-entry.
Click it to open the layout shown in the screenshot above.

When a new name is entered (`peacheese` in the screenshot), a new endpoint is created in the database.
If the channel does not appear in the SlowDash Channel List after some time, click the refresh button above the list.
Reloading the browser page may also be necessary.

To stop, press `Ctrl+C` in the terminal. Run `docker compose down` before starting another example.

### Setup Procedure for Your Project
From the previous example:
1. Create a new SlowTask Python script.
2. Create a new HTML form.
3. Add a new SlowTask entry to the SlowDash configuration file.

#### Step 1
Create `slowtask-manual-entry.py` with the following content:
```python
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

print('hello from manual-entry.py')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')

def write_value(name: str, value: float):
    print(f'writing {name}={value} ')
    dripline.sensor_value_alert(name=name).set(value)
```

#### Step 1
Create `html-manual-entry.html` under `config` with the following content:
```html
<form>
  name: <input name="name" style="width:8em" value="peaches">
  value: <input type="number" name="value" style="width:8em" step="any" value="0">
  <input type="submit" name="manual-entry.write_value()" value="write" style="font-size:130%">
</form>    
```

#### Step 3
Modify the `task` block of `SlowdashProject.yaml` to add the new slowtask
```yaml
  task:
    - name: control-peaches
      auto_load: true
    - name: manual-entry
      auto_load: true
```
or to replace the previous one
```yaml
  task:
    name: manual-entry
    auto_load: true
```


### How It Works
This example demonstrates how to send sensor data values to the Dripline mesh.
Manually entered values are pushed to the Dripline mesh in the same way as other sensor readout values and are stored in the database.

Key feature:
- `dripline.sensor_value_alert(name).set(value)` creates a sensor value alert on the Dripline mesh, typically collected by a sensor logger and stored in the database.


## Example 05: Receiving (Sensor) Data Values from Other Dripline Endpoints
### Objectives
This example shows how to receive data values (typically sensor readouts) from other Dripline endpoints and process them.
In this example, statistics are calculated for each endpoint and pushed to the browser.

| Screenshot |
|------------|
|<img src="FirstMeshReceiveData.png" width="100%">|

### Running the Example
The `05_ReceivingData` directory contains the complete set of files. Run:
```bash
cd 05_ReceivingData
docker compose up
```
Wait for RabbitMQ to become ready (about 30 seconds). Then open a web browser and navigate to `http://localhost:18881`.
On the SlowDash home page, the “SlowDash, SlowPlot, SlowCruise” panel (top right) has an icon labeled count-peaches.
Click it to open the layout shown in the screenshot above.

To stop, press `Ctrl+C` in the terminal. Run `docker compose down` before starting another example.

### Setup Procedure for Your Project
This example can be appended to a previous example, or can replace it.
In addition to the steps in the previous example:

1. Create a new SlowTask Python script that receives data from other endpoints, analyzes it, and sends the results to browsers.
2. Enable the SlowTask script in the SlowDash configuration file.

#### Step 1
Create a `slowtask-count_peaches.py` file under `YOUR/SLOWDASH/PROJECT/config` with the following content:
```python
from slowpy.control import control_system as ctrl
ctrl.import_control_module('AsyncDripline')
dripline = ctrl.async_dripline('amqp://dripline:dripline@rabbit-broker')
print(f'hello from {__name__}')

async def _run():
    endpoint_stats = {}

    while not ctrl.is_stop_requested():
        # receive a data packet from Dripline Mesh
        message = await dripline.sensor_value_queue().aio_get()
        if message is None or message.body is None:
            continue
        endpoint_name = message.parameters['routing_key'].split('.')[1]
        timestamp = message.headers.get('timestamp', None)
        value_raw = message.body.get('value_raw', None)

        # analyze data
        n, sum = endpoint_stats.get(endpoint_name, (0, 0))
        n += 1
        sum += value_raw
        endpoint_stats[endpoint_name] = (n, sum)
    
        # push the analyzed data to SlowDash
        await ctrl.aio_publish(n, name=f'{endpoint_name}.n')
        await ctrl.aio_publish(sum/n, name=f'{endpoint_name}.mean')
```

#### Step 2
Add the following block to your `SlowdashProject.yaml`:
```yaml
  task:
    name: count_peaches
    auto_load: true

  system:
    our_security_is_perfect: true    # enables the Python script editor on the SlowDash web interface
```

### How It Works
Unlike sending, receiving involves waiting and therefore execution can be blocked.
In SlowDash, waiting is handled by asynchronous tasks instead of threads, using the async version of the Dripline module.
This example also shows how to stream data directly to browsers.

Key features:
- Using the async version.
- Receiving a sensor value alert with `message = await dripline.sensor_value_queue().aio_get()`.
- If the `_run()` function is defined in the user script, SlowTask will call it.
- `ctrl.aio_publish(value, name=name)` sends data to browsers. This is similar to `ctrl.export(value, name=name)`, but `aio_publish()` pushes data immediately, whereas `export()` makes data available for browser-driven polling (e.g., via a periodic update timer).

**Data Analysis SlowTask Script (`slowtask-count_peaches.py`)**
- In SlowTask modules, `_initialize()`, `_run()`, and `_finalize()` are called by SlowDash in this order (if defined).
- When the SlowDash system begins shutting down, `ctrl.is_stop_requested()` returns `True`; the user `_run()` must terminate in this case.
- When shutdown is triggered, `sensor_value_queue().aio_get()` returns `None`; otherwise, it awaits a new incoming message.


## Example 06: Handling SET/GET/CMD Requests
### Objectives
This example shows how to create a fully featured Dripline service that handles SET/GET/CMD requests from other Dripline components.
The example sends random-walk data as a proxy for hardware readout data, with multiple parameter settings, each represented by an endpoint.

| Screenshot |
|------------|
|<img src="FirstMeshService.png" width="100%">|

### Running the Example
The `06_HandlingCommands` directory contains the complete set of files. Run:
```bash
cd 06_HandlingCommands
docker compose up
```
Wait for RabbitMQ to become ready (about 30 seconds). Then open a web browser and navigate to `http://localhost:18881`.
On the SlowDash home page, the “SlowDash, SlowPlot, SlowCruise” panel (top right) has an icon labeled randomWalk-control.
Click it to open the layout shown in the screenshot above.

To stop, press `Ctrl+C` in the terminal. Run `docker compose down` before starting another example.

### Setup Procedure for Your Project
From the previous example:
1. Update the SlowTask settings.
2. Create a user Python script (SlowTask) to control the user endpoint.
3. Create another user Python script (SlowTask) to implement the service.

In this example, the HTML form for the control panel is generated by the corresponding SlowTask script.

#### Step 1
Modify the `task` block of `SlowdashProject.yaml` as follows:
```yaml
  task:
    - name: randomwalk-service
      auto_load: true
    - name: control-randomwalk
      auto_load: true
```

#### Step 2
Create `slowtask-control-randomwalk.py` under `config` with the following content:
```python
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')
print(f'hello from {__name__}')

def set_value(value: float):
    print(f'setting randomwalk value to {value}')
    dripline.endpoint('randomwalk_value').set(value)

def set_step(step: float):
    print(f'setting randomwalk step to {step}')
    dripline.endpoint('randomwalk_step').set(step)

def _get_html():
    return '''
      <form>
        <table>
          <tr>
            <td>Value:</td>
            <td><input type="number" name="value" style="width:8em" step="any" value="0"></td>
            <td><input type="submit" name="control-randomwalk.set_value()" value="set" style="font-size:130%"></td>
          </tr>
          <tr>
            <td>Step:</td>
            <td><input type="number" name="step" style="width:8em" step="any" value="1.0"></td>
            <td><input type="submit" name="control-randomwalk.set_step()" value="set" style="font-size:130%"></td>
          </tr>
        </table>
      </form>
    '''
```

#### Step 3
Create another SlowTask Python script named `slowtask-randomwalk-service.py` with the following content:
```python
import asyncio, random

from slowpy.control import control_system as ctrl
ctrl.import_control_module('AsyncDripline')

dripline = ctrl.async_dripline('amqp://dripline:dripline@rabbit-broker', 'RandomWalk')
print(f'hello from {__name__}')


class RandomwalkService:
    def __init__(self):
        self.x = 0
        self.step = 1

    async def on_set(self, message):
        endpoint, value = message.parameters["routing_key"], message.body
        if endpoint == 'randomwalk_value':
            self.x = float(value['values'][0])
            return self.x
        elif endpoint == 'randomwalk_step':
            self.step = abs(float(value['values'][0]))
            await dripline.sensor_value_alert('randomwalk_step').aio_set(self.step)
            return self.step
            
    async def on_get(self, message):
        endpoint, value = message.parameters["routing_key"], message.body
        if endpoint == 'randomwalk_value':
            return self.x
        elif endpoint == 'randomwalk_step':
            return self.step

    async def on_command(self, message):
        endpoint, specifier, value = message.parameters["routing_key"], message.header['specifier'], message.body
        return value
    
    async def run(self):
        await dripline.sensor_value_alert('randomwalk_step').aio_set(self.step)
        while not ctrl.is_stop_requested():
            self.x = random.gauss(self.x, self.step)
            await dripline.sensor_value_alert('randomwalk_value').aio_set(self.x)
            await ctrl.aio_sleep(1)

            
service = RandomwalkService()

async def _run():
    await asyncio.gather(
        dripline.service(service, endpoints=['randomwalk_value', 'randomwalk_step']).aio_start(),
        service.run()
    )

async def _finalize():
    await dripline.aio_close()


    
# make this script independently executable
if __name__ == '__main__':
    from slowpy.dash import Tasklet
    Tasklet().run()
k
```

### How It Works
This example demonstrates how to create a complete Dripline service that handles SET/GET/CMD requests and generates continuous data streams.
The system simulates a hardware device with configurable parameters and real-time data generation.

**RandomWalk Service (`slowtask-randomwalk-service.py`)**
- In SlowTask modules, `_initialize()`, `_run()`, and `_finalize()` are called by SlowDash in this order (if defined, among other hooks).
- The SlowPy node `dripline.service(handler)` receives SET/GET/CMD Dripline commands, forwards them to the service handler, and sends back replies. The `.aio_start()` method creates asynchronous tasks for command processing and heartbeat emission.
- The `RandomwalkService` class is the user service handler:
  - Maintains internal state: current position (`self.x`) and step size (`self.step`), both mapped to Dripline endpoints.
  - The SlowPy node calls the handler’s `on_set()` method upon receiving a Dripline SET request.
  - Similarly, `on_get()` and `on_command()` methods will be called for GET and CMD requests, respectively, if defined.
  - The `run()` method is specific to this example and implements the user loop, including simulating the random walk process and sending out the data.
- The final block with a `Tasklet` allows running this SlowTask as an independent process — useful for distributed multi-node/multi-process deployments or separate Docker containers. (Not used in this example.)

**Control Interface (`slowtask-control-randomwalk.py`)**
- Similar to the control-peaches examples, this SlowTask connects user controls in the web interface to Dripline endpoints.
- Instead of storing a static HTML form, the script dynamically generates the form via `_get_html()`.
