Dripline with SlowDash
======================

## Plotting
<img src="FirstMeshPlotting.png" width="70%" style="box-shadow:0 10px 10px gray">

### Setup Procedure 
```yaml
slowdash_project:
  name: DriplineFirstMesh
  title: Dripline First-Mesh Walkthrough

  data_source:
    url: postgresql://postgres:postgres@postgres:5432/sensor_data
    parameters:
      time_series:
        - schema: numeric_data [sensor_name] @timestamp(with timezone) = value_raw(default), value_cal
```

## Control Endpoints
<img src="FirstMeshControl.png" width="70%" style="box-shadow:0 10px 10px gray">
### Setup Procedure 
```yaml
slowdash_project:
  name: DriplineFirstMesh
  title: Dripline First-Mesh Walkthrough

  data_source:
    url: postgresql://postgres:postgres@postgres:5432/sensor_data
    parameters:
      time_series:
        - schema: numeric_data [sensor_name] @timestamp(with timezone) = value_raw(default), value_cal
      
  task:
    name: control_peaches
    auto_load: true

  system:
    our_security_is_perfect: true    # this will enable the Python script editor on the SlowDash Web interface
```

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

```html
<form>
  value: <input type="number" name="value" style="widtd:8em" step="any" value="0">
  <input type="submit" name="control_peaches.set_peaches()" value="set" style="font-size:130%">
</form>    
```


## Control Endpoints with Slowpy Logic
<img src="FirstMeshControlSlowpy.png" width="70%" style="box-shadow:0 10px 10px gray">
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

```html
<form style="font-size:100%">
  <table>
    <tr>
      <td>Target</td><td>
        <input type="number" name="target" style="widtd:8em" step="any" value="0">
      </td><td></td>
    </tr><tr>
      <td>Ramping</td><td>
        <input type="number" name="ramping_rate" style="widtd:8em" step="any" value="0"> /s
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


## Writing (Sensor) Data Values / Manual Entry
<img src="FirstMeshManualEntry.png" width="70%" style="box-shadow:0 10px 10px gray">

```yaml
  task:
    name: manual-entry
    auto_load: true
```

```python

from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

print('hello from manual-entry.py')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')


def write_value(name:str, value:float):
    print(f'writing {name}={value} ')
    dripline.sensor_value_alert(name=name).set(value)
```

```html
<form>
  name: <input name="name" style="widtd:8em" value="peacheese">
  value: <input type="number" name="value" style="widtd:8em" step="any" value="0">
  <input type="submit" name="manual-entry.write_value()" value="write" style="font-size:130%">
</form>    
```


## Handling SET/GET/CMD Requests
<img src="FirstMeshService.png" width="70%" style="box-shadow:0 10px 10px gray">

```yaml
  task:
    - name: randomwalk-service
      auto_load: true
    - name: control-randomwalk
      auto_load: true
```

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
            
        
    async def on_get(self, message):
        endpoint, value = message.parameters["routing_key"], message.body
        logging.debug(f'GET {endpoint}: {value}')
        
        if endpoint == 'randomwalk_step':
            return self.step
        if endpoint == 'randomwalk':
            return self.x

        
    async def on_command(self, message):
        endpoint, value = message.parameters["routing_key"], message.body
        logging.debug(f'CMD {endpoint}: {value}')
        
        return True

    
    async def run(self):
        await dripline.sensor_value_alert('randomwalk_step').aio_set(self.step)
        while not ctrl.is_stop_requested():
            self.x = random.gauss(self.x, self.step)
            await dripline.sensor_value_alert('randomwalk').aio_set(self.x)
            await ctrl.aio_sleep(1)


            
service = RandomwalkService()


async def _run():
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
