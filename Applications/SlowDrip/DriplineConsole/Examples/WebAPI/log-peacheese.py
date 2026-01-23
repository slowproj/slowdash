import requests

base_url = 'http://localhost:18881/api/slowdrip'
endpoint = 'peacheese'

response = requests.post(f'{base_url}/sensor_value_alert/{endpoint}', json={'value_raw': 200, 'value_cal': 10})
print(response.reason)
