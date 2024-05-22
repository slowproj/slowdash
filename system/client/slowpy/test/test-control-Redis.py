#! /bin/env python3

import slowpy as slp
ctrl = slp.ControlSystem()
ctrl.load_endpoint_module('Redis')
redis = ctrl.redis('redis://localhost:6379/12')

# string key-value
redis.string('name').set('SlowDash')
print(redis.string('name'))

# hash
print(redis.hash("Status"))
print(redis.hash("Status").field("Count"))
redis.hash("Status").field("Count2").set(10)

h = redis.hash("hh")
h.set({'fooo':3, 'bar':5})
print(h)
h.field('foo').set(0)
print(h)

# json
j = redis.json("jj")
j.set({'foo': 'FOO', 'bar': {'buz': 'BUZ', 'qux': 'QUX'}})
print(j)
j.node('bar').node('foo').set(1)
print(j.node('bar'))
