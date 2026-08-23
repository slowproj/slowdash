
import sys, asyncio
from slowpy.control import control_system as ctrl

if len(sys.argv) == 1:
    print(f'Usage: {sys.argv[0]} IP [ MoreIPs .. ]')
    sys.exit(-1)

for ip in sys.argv[1:]:
    http = ctrl.http(f'http://{ip}')
    print('Model: ' + http.path('/od/1008/00').json().get())
    print('Hardware Version: ' + http.path('/od/1009/00').json().get())
    print('Firmware Version: ' + http.path('/od/100a/00').json().get())
    print('MAC Address: ' + http.path('/od/200f/00').json().get())
    print('IP Address: ' + http.path('/od/2010/00').json().get())
