Dripline with SlowDash
======================

This directory contains three docker deployments for different usage levels:
- FirstMesh: Dripline First-Mesh Walkthrough plus SlowDash data visualization (instead of Grafana)
- FirstMeshControl: SlowDash visualization and execution of Dripline python scripts from SlowDash
- FirstMeshControlSlowPy: SlowDash visualization and SlowPy Scripting for full Dripline integration


## __Prependix__: DashStart without configuration
For quick look at existing data on a database, SlowDash can be used without any installation and configuration. 
Just add a SlowDash container in the `docker-compose.yaml` file as below and run `docker compose up -d`:
```yaml
  slowdash:
    image: slowproj/slowdash
    ports:
      - "18881:18881"
    environment:
      - SLOWDASH_INIT_DATASOURCE_URL=postgresql://postgres@postgres:5432/sensor_data
      - SLOWDASH_INIT_TIMESERIES_SCHEMA=numeric_data[sensor_name]@timestamp(aware)=value_raw(default),value_cal
```

Open a web browser and connect to `http://localhost:18881`. 
You will see a list of the Dripine endpoints on the top left panel.
By clicking a endpoint name, a time-series graph will be created.

At this point, there is no persistency. 
In order to save the created panels, you have to setup a SlowDash project as described below (standard installation procedure).


## FirstMesh
This is the minimum addition to the Walkthrough, adding only data visualization with SlowDash.

### Setup Procedure 
Here are the steps to add SlowDash to the FirstMesh Walkthrough. This setup is already done in the `FirstMesh` example directory.

1. Create a SlowDash workspace directory, `slowdash.d`, under the Dripline directory.
2. Create a SlowDash configuration file (`SlowdashProject.yaml`) at the `slowdash.d` directory, with the following contents:
```yaml
slowdash_project:
  name: DriplineFirstMesh
  title: Dripline First-Mesh Walkthrough

  data_source:
    url: postgresql://postgres@postgres:5432/sensor_data
    parameters:
      time_series:
        - schema: numeric_data [sensor_name] @timestamp(with time zone) = value_raw(default), value_cal
```
3. Add SlowDash container entry to the `docker-compose.yaml` file:
```yaml
  slowdash:
    image: slowproj/slowdash
    ports:
      - "18881:18881"
    volumes:
      - ./slowdash.d:/project
```

### Running
```
cd FirstMesh
docker compose up -d
(wait for a few seconds)
docker compose up -d
```
then open a web browser and connect to `http://localhost:18881`

### How it works
For data visualization, SlowDash needs to know at least the location of the data (database URL) and the format of the data ("schema"). The `data_source` section of the SlowDash configuration file describes these.

The schema is basically the names of the table and columns, and describes which columns are for the timestamp, endpoint name, data values, etc.
The SlowDash time-series data schema of
```
  numeric_data [sensor_name] @timestamp(with time zone) = value_raw(default), value_cal
```
corresponds to the SQL table of
```
CREATE TABLE numeric_data (
  sensor_name text NOT NULL,
  "timestamp" timestamp with time zone NOT NULL default now(),
  value_raw double precision NOT NULL,
  value_cal double precision
);
```
which is defined in the Dripline's PostgreSQL configuration.

## FirstMeshControl
In this example we integrate a Dripline Python script with SlowDash so that functions in the script can be called from the GUI.
The Dripline Python script must be placed under the `slowdash.d/config` directory with a name like `slowtask-XXX.py`.

This uses a docker image that includes both Dripline and SlowDash. First build the image by running `make` at the `SlowDrip` directory:
```
make
```
This runs the following command, which builds a SlowDash image using a Dripline image as its base image:
```
cd ../..; docker build --build-arg BASE_IMAGE=driplineorg/dripline-python:v4.7.1 -t slowdash-dripline .
```

If the FirstMesh containers are running, stop it before starting FirstMeshControl:
```
# (at the FirstMesh directory)
docker compose stop
cd ..
```


### Running
```
cd FirstMeshControl
docker compose up -d
(wait for a few seconds)
docker compose up -d
```
then open a web browser and connect to `http://localhost:18881`. From the SlowDash home page, open the `peaches-control` SlowPlot page. You will see a control panel to set the peaches value.


### How it works
The script file is `FirstMeshControl/slowdash.d/config/slowtask-control-peaches.py`:
```python
import dripline
ifc = dripline.core.Interface(dripline_config={'auth-file':'/authentications.json'})

def set_peaches(value, **kwargs):
    print(f'setting peaches to {value}')
    ifc.set('peaches', value)
```

Files with a name like `slowtask-XXX.py` at the `config` directory are automatically scanned by SlowDash. For security reasons, the scripts are not automatically "loaded", and an operator must click `start` manually by default. Auto-loading can be enabled by making an entry in the `SlowdashProject.yaml` configuration file (optional):
```
  task:
    name: control-peaches
    auto_load: true
```

Once the script is loaded, the functions in the script can be called from SlowDash GUI. An easy way to do it is to make a HTML form panel with the content like:
```html
<form>
  value: <input type="number" name="value" value="0">
  <input type="submit" name="control-peaches.set_peaches()" value="set">
</form>    
```
This creates one input field (bound to a parameter `value`) and one button (bound to a function `control-peaches.set_peaches()`. When the button is clicked, the function in the Python script is called with the parameters defined in the form.

As all the parameters in the form will be passed to the function call, it would be a good practice to have the `**kwargs` in the Python function parameter list, otherwise adding an extra `<input>` in the form might cause a Python run-time error.


## FirstMeshControlSlowpy
In this example the Python library part of the SlowDash (`slowpy`) is used to interface with Dripline for full integration, such as exporting control variables in the script to the SlowDash GUI, in addition to function calls from GUI as done in the previous example. 

This uses a docker image that includes both Dripline and SlowDash. Build the image as described in the FirstMeshControl section if it has not been done yet.

If the FirstMesh(Control) containers are running, stop it before starting FirstMeshControlSlowpy:
```
# (at the FirstMesh(Control) directory)
docker compose stop
cd ..
```

### Running
```
cd FirstMeshControlSlowpy
docker compose up -d
(wait for a few seconds)
docker compose up -d
```
then open a web browser and connect to `http://localhost:18881`. From the SlowDash home page, open the `peaches-control` SlowPlot page. You will see a control panel to set the peaches value with the ramping feature, and a table showing the control status (i.e., the values of the control variables and process variables in the Python script).


### How it works
The script file is `FirstMeshControlSlowpy/slowdash.d/config/slowtask-control-peaches.py`:
```python
from slowpy.control import ControlSystem, ControlNode
ctrl = ControlSystem()

ctrl.import_control_module('Dripline')
dripline = ctrl.dripline(dripline_config={'auth-file':'/authentications.json'})

peaches = dripline.endpoint("peaches")


def set_peaches(target, ramping, **kwargs):
    print(f'setting peaches to {target}, with ramping at {ramping}')
    peaches.ramping(ramping).set(target)

    
class StatusNode(ControlNode):
    def get(self):
        return {
            'target': peaches.ramping().get(),
            'ramping': peaches.ramping().status().get()
        }

    
def _export():
    return [
        ('peaches', peaches),
        ('status', StatusNode())
    ]
```

The Dripline interfacing is done via a SlowPy control object (`peaches`) bound to a Dripline endpoint. The `set(value)` method of the control object writes the value to the endpoint, and `get()` method reads a value. In addition, the SlowPy control objects can be directly exported to SlowDash GUI for quasi-realtime displaying and modifying. Also the object implements some common control functions such as `ramping()`. See the "Controls" section of the SlowDash documentation for details.


## Security Considerations
SlowDash is designed to be used within a secured network. External access should be done through VPN and/or SSH tunnel. Under this assumption, SlowDash trusts all the users.

Despite this, Python script uploading and editing through its Web pages are disabled by the SlowDash default settings. Here for the Dripline-SlowDash applications, this is explicitly enabled in the `SlowdashProject.yaml` configuration file by:
```yaml
  system:
    our_security_is_perfect: true
```
If `our_security_is_perfect` is not `true`, users will have to log-in to the system and edit the files in the usual way.

If needed, the access to the SlowDash page can be protected by the HTTP basic authentication:
```yaml
  authentication:
    type: Basic
    key: hachi:$2a$12$V/5o6No5eeCRUBrUMi7wee8vYKtFijp18oWsVulFQ4JMAAtpDhPOa
    
```
See the "Project Setup" section of the SlowDash document for details.

It is possible to specify which SlowDash configuration file to use at the time of starting. Running multiple SlowDash instances with different configurations, such as one for unlimited access for limited users and another for limited access for unlimited users, might be useful. SlowDash currently does not implement user role management.
