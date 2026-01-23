import requests

url = "http://localhost:18881"
endpoint = "peaches"

response = requests.get(f"{url}/api/slowdrip/endpoint/{endpoint}")
print(f"{response.reason}: {response.text}")

value = response.json().get("value_raw", None)
new_value = value + 1

response = requests.post(f"{url}/api/slowdrip/endpoint/{endpoint}", json=new_value)
print(response.reason)
