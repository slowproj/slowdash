import requests

url = "http://localhost:18881"
endpoint = "peacheese"

response = requests.post(f"{url}/api/slowdrip/sensor_value_alert/{endpoint}", json={"value_raw": 200, "value_cal": 10})
print(response.reason)
