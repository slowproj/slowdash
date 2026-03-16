
import time

from slowpy.control import control_system as ctrl
redis = ctrl.import_control_module('Redis').redis('redis://localhost:6379/12')


# string
redis.string('name').set('SlowDash')
print(redis.string('name'))

# hash
redis.hash("Status").field("Count").set(10)
print(redis.hash("Status"))
print(redis.hash("Status").field("Count"))

# time-series
redis.ts('ch00').current().set(123)
redis.ts('ch00').set([(int(1000*(time.time()-100)), 456)])
print(redis.ts('ch00'))
print(redis.ts('ch00').last().time())
print(redis.ts('ch00').last().lapse())

# JSON
j = redis.json("jj")
j.set({'foo': 'FOO', 'bar': {'buz': 'BUZ', 'qux': 'QUX'}})
print(j)
j.node('bar').node('foo').set(1)
print(j.node('bar'))
