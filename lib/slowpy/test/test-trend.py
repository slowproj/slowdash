#! /usr/bin/env python3        


import numpy as np
import slowpy as slp

import time
start = int(time.time() - 100)
rate_trend = slp.RateTrend('test_ratetrend_00', start=start, length=300, tick=10)
value_trend = slp.Trend('test_trend_00', start=start, length=300, tick=10)


for lapse in range(0, 350, 1):
    t = start + lapse
    n = np.random.poisson(10)
    for i in range(n):
        rate_trend.fill(t)

        x = np.random.normal(10, 3)
        value_trend.fill(t, x)

print(rate_trend)  # as a graph
print()
print(rate_trend.timeseries())  # as time-series
print()
print(value_trend.timeseries())
