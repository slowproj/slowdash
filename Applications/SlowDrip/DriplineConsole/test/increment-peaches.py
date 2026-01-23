url = 'http://localhost:18881/api/slowdrip/endpoint/peaches'

import requests
response = requests.get(url)

print(f'{response.reason}: {response.text}')
value = response.json().get('value_raw')

response = requests.post(url, json=value+1)
print(response.reason)
