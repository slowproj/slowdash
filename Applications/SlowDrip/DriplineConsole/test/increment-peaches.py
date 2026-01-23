import requests

url = 'http://localhost:18881/api/slowdrip/endpoint/peaches'

response = requests.get(url)
print(f'{response.reason}: {response.text}')

value = response.json().get('value_raw')
new_value = value + 1

response = requests.post(url, json=new_value)
print(response.reason)
