#! /bin/env python3

from slowpy.control import ControlSystem

ctrl = ControlSystem()
slowdash = ctrl.http('http://localhost:18881').slowdash()


print("ping -> ", slowdash.ping())
print("config -> ", slowdash.config())
print("channels -> ", slowdash.channels())
print("data/ch0,ch1 -> ", slowdash.data('ch0,ch1',length=60))


print(slowdash.config_file('slowplot-trash.json').set('{"message": "hello"}'))
print(slowdash.config_file('slowplot-trash.json'))
