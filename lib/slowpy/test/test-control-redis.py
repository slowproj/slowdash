#! /bin/env python3

from slowpy.control import ControlSystem
ctrl = ControlSystem()
ctrl.load_control_module('Redis')
redis = ctrl.redis('redis://localhost:6379/12')


# string
redis.string('name').set('SlowDash')
print(redis.string('name'))


# hash
print(redis.hash("Status"))
print(redis.hash("Status").field("Count"))
redis.hash("Status").field("Count2").set(10)


# time-series
print(redis.ts('ch00'))
print(redis.ts('ch00').last())
print(redis.ts('ch00').last().time())
print(redis.ts('ch00').last().lapse())

import time
redis.ts('ts00').current().set(123)
redis.ts('ts00').set([(int(1000*(time.time()-100)), 456)])
print(redis.ts('ts00'))
print(redis.ts('ts00').last().lapse())



# JSON
j = redis.json("jj")
j.set({'foo': 'FOO', 'bar': {'buz': 'BUZ', 'qux': 'QUX'}})
print(j)
j.node('bar').node('foo').set(1)
print(j.node('bar'))


