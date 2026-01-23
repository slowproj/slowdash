
base_url = 'http://localhost:18881/api/slowdrip'

import requests
response = requests.post(f'{base_url}/sensor_value_alert/peacheese', json={'value_raw': 200, 'value_cal': 10})
print(response.reason)
