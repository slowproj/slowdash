Dripline with SlowDash
======================

This directory includes three docker deployments for different usage depths:
- First Mesh: add only SlowDash GUI to the Dripline First-Mesh Walkthrough
- First Mesh Control: add SlowDash GUI and execution of Dripline python scripts
- First Mesh Control by SlowPy: add SlowDash GUI and SlowPy Scripting to fully integrate Dripline

## FirstMesh
### Usage
```
cd FirstMesh
docker compose up -d
(wait for a few seconds)
docker compose up -d
```
then open a web browser and connect to `http://localhost:18881`



## FirstMeshControl
This uses a docker image that includes both Dripline and SlowDash. First build this image by running `make` at the `SlowDrip` directory:
```
make
```

### Usage
```
cd FirstMeshControl
docker compose up -d
(wait for a few seconds)
docker compose up -d
```
then open a web browser and connect to `http://localhost:18881`



### How it works
The script file is `FirstMeshControl/slowdash.d/config/slowtask-control-peaches.py`:
```python
import dripline
ifc = dripline.core.Interface(dripline_config={'auth-file':'/authentications.json'})

def set_peaches(value, **kwargs):
    print(f'setting peaches to {value}')
    ifc.set('peaches', value)
```

To have the script file recognized by SlowDash, the file must be placed under the `config` direcotry and the name must start with `slowtask-`.

The functions in the script can be called from SlowDash GUI. An easy way to do it is to make a HTML form panel with the content like:
```html
<form>
  value: <input type="number" name="value" style="widtd:8em" step="any" value="0">
  <input type="submit" name="control-peaches.set_peaches()" value="set" style="font-size:130%">
</form>    
```
This creates one input field and one button. When the button is clicked, the function in the Python script is called with parameters defined in the form (`value` in this example).




## FirstMeshControlSlowpy
This uses a docker image that includes both Dripline and SlowDash. Build the image as described in the FirstMeshControl section if it has not been done.

### Usage
```
cd FirstMeshControlSlowpy
docker compose up -d
(wait for a few seconds)
docker compose up -d
```
then open a web browser and connect to `http://localhost:18881`


### How it works
The script file is `FirstMeshControl/slowdash.d/config/slowtask-control-peaches.py`:
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

This time, the Dripline interfacing is done via a SlowPy control object ('peaches') mapped to an Dripline endpoint. The `set()` method of the control object write the value to the endpoint, and `get()` method reads a value. In addition, the SlowPy control object can be directly exported to SlowDash GUI for displaying and modifying. Also the object implementes some common control functions such as `ramping()`. See the "Controls" section of the SlowDash documentation for full details.
