Dripline with SlowDash
======================

This directory contains three docker deployments for different usage levels:
- FirstMesh: Dripline First-Mesh Walkthrough plus SlowDash data visualization (instead of Grafana)
- FirstMeshControl: SlowDash visualization and execution of Dripline python scripts from SlowDash
- FirstMeshControlSlowPy: SlowDash visualization and SlowPy Scripting for full Dripline integration


## FirstMesh
This is the minimum addittion to the Walkthrough, adding only the data visualization with SlowDash.

### Setup Procedure (already done in the `FirstMesh` directory)
1. Create a SlowDash directory, `slowdash.d`, under the Dripline working directory.
2. Create a SlowDash configuration file (`SlowdashProject.yaml`) at the `slowdash.d` directory, with the following contents:
```yaml
slowdash_project:
  name: DriplineFirstMesh
  title: Dripline First-Mesh Walkthrough
  data_source:
    url: postgresql://postgres@postgres:5432/sensor_data
    parameters:
      time_series:
        - schema: numeric_data [sensor_name] @timestamp(aware) = value_raw(default), value_cal
```
1. Add SlowDash container entry to the `docker-compose.yaml` file:
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

Scripts with a name like `slowtask-XXX.py` at the `config` directory are automatically scanned by SlowDash. For security reasons, the script is not automatically "loaded", and an operator must click `start` manually by default. Auto-loading can be enabled by making an entry in the `SlowdashProject.yaml` configuration file (optional):
```
  task:
    name: control-peaches
    auto_load: true
```

Once the scripot is loaded, the functions in the script can be called from SlowDash GUI. An easy way to do it is to make a HTML form panel with the content like:
```html
<form>
  value: <input type="number" name="value" value="0">
  <input type="submit" name="control-peaches.set_peaches()" value="set">
</form>    
```
This creates one input field (bound to a parameter `value`) and one button (bound to a function `control-peaches.set_peaches()`. When the button is clicked, the function in the Python script is called with the parameters defined in the form.

As all the parameters in the form will be passed to the function call, it would be a good practice to have the `**kwargs` in the Python function parameter list, otherwise adding an extra `<input>` in the form might cause a Python run-time error.


## FirstMeshControlSlowpy
In this example the SlowPy library (Python library part of the SlowDash system) is used to interface with Dripline for full integration, such as exporting control variables in the script to the SlowDash GUI, in addition to function calls from GUI. Also some control logics in the SlowDash Python library (`slowpy`) become avaiable, such as ramping the set values at a given rate etc.

This uses a docker image that includes both Dripline and SlowDash. Build the image as described in the FirstMeshControl section if it has not been done.

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

The Dripline interfacing is done via a SlowPy control object ('peaches') bound to a Dripline endpoint. The `set(value)` method of the control object writes the value to the endpoint, and `get()` method reads a value. In addition, the SlowPy control objects can be directly exported to SlowDash GUI for displaying and modifying, as access to control/process variables of a control system. Also the object implementes some common control functions such as `ramping()`. See the "Controls" section of the SlowDash documentation for details.


## Security Considerations
SlowDash is designed to be used within a secured network. External access should be done through VPN and/or SSH tunnel. Under this assumption, SlowDash trusts all the users.

Despite this, Python script uploading and editting through its Web pages are disabled by the SlowDash default settings. Here for the Dripline-SlowDash applications, this is explicitly enabled in the `SlowdashProject.yaml` configuration file by:
```yaml
  system:
    our_security_is_perfect: true
```
If `our_secirity_is_perfect` is not `true`, users will have to log-in to the system and edit the files in the usual way.

If needed, the access to the SlowDash page can be protedted by the HTTP basic authentication:
```yaml
  authentication:
    type: Basic
    key: hachi:$2a$12$V/5o6No5eeCRUBrUMi7wee8vYKtFijp18oWsVulFQ4JMAAtpDhPOa
    
```
See the "Project Setup" section of the SlowDash document for details.

It is possible to specify which SlowDash configuration file to use at the time of starting. Running multiple SlowDash instances with different configurations, such as one for unlimited access for limited users and another for limited access for unlimited users, might be useful. SlowDash currently does not implement user role management.
