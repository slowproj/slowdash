Dripline Console
================
## Features
- Web GUI for
  - Listing sensor values without going through database
  - Listing Dripline service heartbeats
  - Sending SET/GET/CMD commands to endpoints
- Web API for
  - Setting and getting endpoint values
  - Alerting a value for logging (sensor_value_alert)

| Screenshot |
|------------|
| <img src="DriplineConsole.png" width="100%"> |


## Setup
Copy the `slowdash.d/config/slowtask-DriplineConsole.py` file to your SlowDash configuration directory,
and enable the slowatsk in your `SlowdashProject.yaml`:
```yaml
  task:
    name: DriplineConsole
    auto_load: true
```
The plot layout and HTML forms are included in the SlowTask.


## Web API
Dripline Console provides a convenient API that can be used through HTTP. Using the API does not require any library such as Dripline or SlowDash; you can get and set endpoint values with standard tools like the `curl` command or the `request` Python module. There are some additional overhead by going through HTTP, and for a long-term applications, using the Dripline or SlowDrip library (described in SlowDrip/FirstmeshWalkthrough) is recommended.

### Usage
See bash and Python examples under `DriplineConsole/Examples/WebAPI`.

- to get an endpoint value: GET `http://HOST:PORT/api/slowdrip/endpoint/ENDPOINT`
- to set an endpoint value: POST `http://HOST:PORT/api/slowdrip/endpoint/ENDPOINT` with data (JSON) in body
- to send a value for logging: POST `http://HOST:PORT/api/slowdrip/sensor_value_alert/NAME` with data (JSON) in body

### Python Examples
#### Increamenting an endpoint value
```python
import requests

url = 'http://localhost:18881/api/slowdrip/endpoint/peaches'

response = requests.get(url)
print(f'{response.reason}: {response.text}')

value = response.json().get('value_raw')
new_value = value + 1

response = requests.post(url, json=new_value)
print(response.reason)
```

#### Logging a value
```python
import requests

base_url = 'http://localhost:18881/api/slowdrip'
endpoint = 'peacheese'

response = requests.post(f'{base_url}/sensor_value_alert/{endpoint}', json={'value_raw': 200, 'value_cal': 10})
print(response.reason)
```


### Bash Examples
#### Getting an endpoint value
```bash
#! /bin/bash

URL="http://localhost:18881/api/slowdrip/endpoint/peaches"

value=$(curl -s "$URL")
echo ${value}
```

#### Logging a value
```bash
#! /bin/bash

curl -X POST http://localhost:18881/api/slowdrip/sensor_value_alert/peacheese --data '{"value_raw":200, "value_cal":10}'
```
