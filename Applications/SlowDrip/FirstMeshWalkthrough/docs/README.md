Dripline with SlowDash
======================
This document demonstrates how to integrate SlowDash with Dripline.
It provides a series of step-by-step examples, from basic visualization to fully functional Dripline services.

- Example 1: Adding SlowDash data visualization to Dripline
- Example 2: Sending SET/GET/CMD commands to Dripline endpoints
- Example 3: Controlling Dripline endpoints with SlowDash Python library (SlowPy)
- Example 4: Sending (sensor) data values to the Dripline Mesh / Entering manual values
- Example 5: Handling SET/GET/CMD commands from other Dripline services


## Plotting
### Objectives
This example shows how to add SlowDash data visualization to the Dripline First-Mesh Walkthrough.

| Screenshot |
|------------|
|<img src="FirstMeshPlotting.png" width="100%">|

### Running the Example
The `01_Plotting` directory includes the complete set of files. Run `docker compose` at the directory:
```bash
cd 01_Plotting
docker compose up
```
Wait for RabbitMQ to become ready (approximately 30 seconds). Then open a web browser and navigate to `http://localhost:18881`. On the SlowDash home page, the Data Channels panel (top left) shows a list of data channels (endpoints). Clicking a channel name will create an initial layout with a plot panel. You can modify the panel and add more panels to the layout.

To stop, press `Ctrl+C` in the terminal. Run `docker compose down` before running another example.

### Setup Procedure for your project
1. Add a SlowDash container in your docker compose
2. Optionally, make a SlowDash working directory (`slowdash.d` in the example)
3. Write a SlowDash configuration file

#### Step 1
Append the following block to your `docker-compose.yaml`
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
Create a `SlowdashProject.yaml` file with the following contents:
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

### How it works
For data visualization, SlowDash needs to know at least the location of the data (database URL) and the format of the data ("schema").
The `data_source` section of the SlowDash configuration file describes these.

The schema is basically the names of the table and columns, and describes which columns are for the timestamps, endpoint names, data values, etc. The SlowDash time series data schema of
```yaml
      time_series:
        schema: numeric_data [sensor_name] @timestamp(with timezone) = value_raw(default), value_cal
```
corresponds to a SQL table of
```sql
CREATE TABLE numeric_data (
  sensor_name TEXT NOT NULL,
  "timestamp" TIMESTAMP WITH TIMEZONE NOT NULL DEFAULT NOW(),
  value_raw DOUBLE PRECISION NOT NULL,
  value_cal DOUBLE PRECISION
);
```
which is defined in the Dripline's PostgreSQL configuration (FirstMesh Walkthrough).

## Controlling Endpoints
### Objectives
This example shows:
- How to bind user Python code to SlowDash GUI
- How to send SET/GET/CMD commands to Dripline endpoints from user Python code

| Screenshot |
|------------|
|<img src="FirstMeshControl.png" width="100%">|

### Running the Example
The `02_Control` directory includes the complete set of files. Run `docker compose` at the directory:
```bash
cd 02_Control
docker compose up
```
Wait for RabbitMQ to become ready (approximately 30 seconds). Then open a web browser and navigate to `http://localhost:18881`.
On the SlowDash home page, the "SlowDash, SlowPlot, SlowCruise" panel (top right) has one icon titled "Control Peaches".
Clicking it will open a layout as shown in the screenshot above.

To stop, press `Ctrl+C` in the terminal. Run `docker compose down` before running another example.

### Setup Procedure for your project
In addition to the steps in the previous example,

1. Create a user Python script (SlowTask) that receives user operations and controls the endpoints
2. Create an HTML form for the control panel
3. Enable the Python script in the SlowDash configuration file

#### Step 1
Create a `slowtask-ControlPeaches.py` file under `YOUR/SLOWDASH/PROJECT/config` directory with the following contents:
```python
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

print('hello from control_peaches.py')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')
peaches = dripline.endpoint('peaches')

def set_peaches(value:float):
    print(f'setting peaches to {value}')
    peaches.set(value)
```

#### Step 2
Create a `html-ControlPeaches.html` file under `config` directory with the following contents:
```html
<form>
  value: <input type="number" name="value" style="width:8em" step="any" value="0">
  <input type="submit" name="control_peaches.set_peaches()" value="set" style="font-size:130%">
</form>    
```

#### Step 3
Add the following block to your `SlowdashProject.yaml` file:
```yaml
  task:
    name: control_peaches
    auto_load: true

  system:
    our_security_is_perfect: true    # this will enable the Python script editor on the SlowDash Web interface
```

### How it works
This example demonstrates the integration between SlowDash's web interface and Dripline's control system through SlowTask scripts. Here's how the components work together:

**SlowTask Script (`slowtask-ControlPeaches.py`)**:
- Imports the Dripline control module through SlowPy's dynamic plugin loading and establishes a connection to the RabbitMQ broker
- Creates a reference to the 'peaches' endpoint using `dripline.endpoint('peaches')`, through SlowPy's node chain mechanism.
- The user function `set_peaches()` is automatically exposed to the web interface through SlowDash's task system

**HTML Form (`html-ControlPeaches.html`)**:
- Provides a simple web form with a number input field for the value
- The submit button triggers the `control_peaches.set_peaches()` function 
- The function parameter values are taken from other input fields of the form. Parameters are bound by names, and type mismatches will create an error response without calling the user function.

**Configuration (`SlowdashProject.yaml`)**:
- The `task` section defines the SlowTask with `auto_load: true` to automatically load the script
- The `system.our_security_is_perfect: true` setting enables the Python script editor in the web interface; remove this section if there are any security concerns.


## Controlling Endpoints with Slowpy Logic
### Objectives
By advancing the previous example, this example shows:
- How to use control logics (such as ramping) in SlowDash Python library (SlowPy)
- How to send data directly from user Python to SlowDash GUI


| Screenshot |
|------------|
|<img src="FirstMeshControlSlowpy.png" width="100%">|

### Running the Example
The `03_ControlSlowpy` directory includes the complete set of files. Run `docker compose` at the directory:
```bash
cd 03_ControlSlowpy
docker compose up
```
Wait for RabbitMQ to become ready (approximately 30 seconds). Then open a web browser and navigate to `http://localhost:18881`.

To stop, press `Ctrl+C` in the terminal. Run `docker compose down` before running another example.
On the SlowDash home page, the "SlowDash, SlowPlot, SlowCruise" panel (top right) has one icon titled "Control Peaches".
Clicking it will open a layout as shown in the screenshot above.

### Setup Procedure for your project
In addition to the steps in the previous example,
1. Modify the user Python script (SlowTask) to add more features
2. Modify the HTML form for additional controls

#### Step 1
Replace the `slowtask-ControlPeaches.py` file from the previous example with the following contents:
```python
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

print('hello from control_peaches.py')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')
peaches = dripline.endpoint('peaches').value_raw()

def set_peaches(target:float, ramping_rate:float):
    print(f'setting peaches to {target}, with ramping at {ramping_rate}')
    peaches.ramping(ramping_rate).set(target)
    
def abort_ramping():
    peaches.ramping().status().set(0)
    
ctrl.export(peaches.ramping(), name='ramping_target')
ctrl.export(peaches.ramping().status(), name='ramping_status')
```

#### Step 2
Replace the `html-ControlPeaches.html` file from the previous example with the following contents:
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

### How it works

This example extends the basic control functionality by introducing SlowPy control logic and direct data connection from user scripts to web browser without going through the database. In this example, ramping control is added to endpoint value setting.

**SlowTask Script (`slowtask-ControlPeaches.py`)**:
- `peaches.ramping(rate)` attaches a SlowPy ramping logic node to the `peaches` node.
- Similarly, `.status()` attaches a status node to the ramping node.
- Setting a value (calling `set(value)`) to the ramping node will start a ramping sequence to its attaching node (i.e., `peaches`).
- Setting `0` to the status node stops ramping of its attaching node (i.e., `peaches.ramping()`).
- SlowPy node values can be exported to external systems such as web browsers, by `ctrl.export()`.


## Writing (Sensor) Data Values / Manual Entry
### Objectives
This example shows how to send Dripline alert messages (such as sensor value alerts), with an application of manually putting data from the SlowDash GUI.

| Screenshot |
|------------|
|<img src="FirstMeshManualEntry.png" width="100%">|

### Running the Example
The `04_ManualEntry` directory includes the complete set of files. Run `docker compose` at the directory:
```bash
cd 04_ManualEntry
docker compose up
```
Wait for RabbitMQ to become ready (approximately 30 seconds). Then open a web browser and navigate to `http://localhost:18881`.
On the SlowDash home page, the "SlowDash, SlowPlot, SlowCruise" panel (top right) has one icon titled "Manual Entry".
Clicking it will open a layout as shown in the screenshot above.

To stop, press `Ctrl+C` in the terminal. Run `docker compose down` before running another example.

### Setup Procedure for your project
From the previous example,
1. Change the SlowTask name from `control_peaches` to `manual_entry`
2. Create a new SlowTask Python script and replace the old one
3. Create a new HTML form for manual entry and replace the old one

#### Step 1
Modify the `task` block of the `Slowdash.yaml` file as follows:
```yaml
  task:
    name: manual-entry
    auto_load: true
```

#### Step 2
Delete the old `slowtask-control-peaches.py` file, and create a `slowtask-manual-entry.py` with the following contents:
```python
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

print('hello from manual-entry.py')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')

def write_value(name:str, value:float):
    print(f'writing {name}={value} ')
    dripline.sensor_value_alert(name=name).set(value)
```

#### Step 3
Delete the old `html-control-peaches.html` file, and create a `html-manual-entry.html` file under `config` with the following contents:
```html
<form>
  name: <input name="name" style="width:8em" value="peaches">
  value: <input type="number" name="value" style="width:8em" step="any" value="0">
  <input type="submit" name="manual-entry.write_value()" value="write" style="font-size:130%">
</form>    
```

### How it works
This example demonstrates how to send sensor data values to the Dripline mesh. In this example, manually entered values are pushed to the Dripline mesh in the same way as all the other sensor readout values, to be stored in the database.

**Manual Entry SlowTask Script (`slowtask-manual-entry.py`)**:
- `dripline.sensor_value_alert(name)` will create a new SlowPy node to send alert messages.


## Handling SET/GET/CMD Requests
### Objectives
Finally, this example shows how to make a fully featured Dripline service, which handles SET/GET/CMD requests from other Dripline services. 
This example sends out random walk data as a proxy of hardware readout data, with multiple parameter settings each of which is an endpoint.

| Screenshot |
|------------|
|<img src="FirstMeshService.png" width="100%">|

### Running the Example
The `05_Service` directory includes the complete set of files. Run `docker compose` at the directory:
```bash
cd 05_Service
docker compose up
```
Wait for RabbitMQ to become ready (approximately 30 seconds). Then open a web browser and navigate to `http://localhost:18881`.
On the SlowDash home page, the "SlowDash, SlowPlot, SlowCruise" panel (top right) has one icon titled "randomWalk-control".
Clicking it will open a layout as shown in the screenshot above.

To stop, press `Ctrl+C` in the terminal. Run `docker compose down` before running another example.

### Setup Procedure for your project
From the previous example,
1. Update the SlowTask settings
2. Create a user Python code (SlowTask) to control the user endpoint
3. Create another user Python code (SlowTask) to implement the service

In this example, the HTML form for the control panel is generated by the corresponding SlowTask script.

#### Step 1
Modify the `task` block of the `Slowdash.yaml` file as follows:
```yaml
  task:
    - name: randomwalk-service
      auto_load: true
    - name: control-randomwalk
      auto_load: true
```

#### Step 2
Delete the old SlowTask script under `config`, and create a `slowtask-control-randomwalk.py` with the following contents:
```python
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

print('hello from control-randomwalk.py')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')

def set_value(value:float):
    print(f'setting randomwalk value to {value}')
    dripline.endpoint('randomwalk').set(value)

def set_step(step:float):
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
Create another SlowTask Python script named as `slowtask-randomwalk-service.py` under `config` with the following contents:
```python
import asyncio, random, logging

from slowpy.control import control_system as ctrl
ctrl.import_control_module('AsyncDripline')

print(f'hello from {__name__}')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')


class RandomwalkService:
    def __init__(self):
        self.x = 0
        self.step = 1

    async def on_set(self, message):
        endpoint, value = message.parameters["routing_key"], message.body
        logging.debug(f'SET {endpoint}: {value}')
        
        if endpoint == 'randomwalk_step':
            self.step = abs(float(value['values'][0]))
            await dripline.sensor_value_alert('randomwalk_step').aio_set(self.step)
            return True
        if endpoint == 'randomwalk':
            self.x = float(value['values'][0])
            return True
        
    async def run(self):
        await dripline.sensor_value_alert('randomwalk_step').aio_set(self.step)
        while not ctrl.is_stop_requested():
            self.x = random.gauss(self.x, self.step)
            await dripline.sensor_value_alert('randomwalk').aio_set(self.x)
            await ctrl.aio_sleep(1)


async def _run():
    service = RandomwalkService()
    await asyncio.gather(
        dripline.service(service, endpoints='*').aio_start(),
        service.run()
    )

async def _finalize():
    await dripline.aio_close()


if __name__ == '__main__':
    from slowpy.dash import Tasklet
    Tasklet().run()
```

### How it works
This example demonstrates how to create a complete Dripline service that handles SET/GET/CMD requests and generates continuous data streams. The system simulates a hardware device with configurable parameters and real-time data generation.

**Service Architecture**:

**RandomWalk Service (`slowtask-randomwalk-service.py`)**:
- The SlowPy node, `dripline.service(handler)`, receives the SET/GET/CMD Dripline commands, passes them to the service handler, and sends back the reply. The `.aio_start()` method creates an asynchronous task.

- The user `RandomwalkService` class is a service handler that simulates a hardware device:
  - Maintains internal state: current position (`self.x`) and step size (`self.step`), both corresponding to a Dripline endpoint
  - The SlowPy node calls user's `on_set()` when it receives a Dripline SET request.
  - Similarly, `on_get()` and `on_command()` will be called for the GET and CMD requests, respectively, if defined
  - The `run()` method starts an asynchronous task to produce the random walk data

**Control Interface (`slowtask-control-randomwalk.py`)**:
- Similar to the control-peaches examples, this SlowTask connects user controls on the Web Interface to the Dripline endpoints.
- Instead of storing a static HTML form, this script dynamically generates the HTML form using the `_get_html()` function
