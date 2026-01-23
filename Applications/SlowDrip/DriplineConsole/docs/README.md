Dripline Console
================
## Features
- Web GUI for
  - Listing sensor values without going through the database
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
Dripline Console provides a convenient API accessible via HTTP. Using the API does not require any library such as Dripline or SlowDash; you can get and set endpoint values with standard tools like the `curl` command or the `request` Python module. There is some additional overhead by going through HTTP, and for long-term applications, using the Dripline or SlowDrip library (described in SlowDrip/FirstmeshWalkthrough) is recommended.

### Usage
See bash and Python examples under `DriplineConsole/Examples/WebAPI`.

- to get an endpoint value: GET `http://HOST:PORT/api/slowdrip/endpoint/ENDPOINT`
- to set an endpoint value: POST `http://HOST:PORT/api/slowdrip/endpoint/ENDPOINT` with data (JSON) in body
- to send a value for logging: POST `http://HOST:PORT/api/slowdrip/sensor_value_alert/NAME` with data (JSON) in body

### Bash/Commandline Examples
(Modify the SlowDash server address accordingly)

#### Getting an endpoint value
```bash
curl http://localhost:18881/api/slowdrip/endpoint/peaches
```

#### Setting an endpoint value
```bash
curl -X POST http://localhost:18881/api/slowdrip/endpoint/peaches --data '200'
```

#### Logging a value
```bash
curl -X POST http://localhost:18881/api/slowdrip/sensor_value_alert/peacheese --data '{"value_raw":200, "value_cal":10}'
```

### Python Examples
#### Incrementing an endpoint value (get and set)
```python
import requests

url = "http://localhost:18881"
endpoint = "peaches"

response = requests.get(f"{url}/api/slowdrip/endpoint/{endpoint}")
print(f"{response.reason}: {response.text}")

value = response.json().get("value_raw", None)
new_value = value + 1

response = requests.post(f"{url}/api/slowdrip/endpoint/{endpoint}", json=new_value)
print(response.reason)
```

#### Logging a value (alert)
```python
import requests

url = "http://localhost:18881"
endpoint = "peacheese"

response = requests.post(f"{url}/api/slowdrip/sensor_value_alert/{endpoint}", json={"value_raw": 200, "value_cal": 10})
print(response.reason)
```
