#! /usr/bin/env python3        


import numpy as np
import slowpy.data as sd


h = sd.Histogram('test_histogram_00', 100, 0, 10)
h.add_attr('color', 'red')
h.add_stat(sd.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))
h.add_stat(sd.HistogramCountStat(0, 10))
for i in range(1000):
    h.fill(np.random.normal(5, 2))
print(h)


g = sd.Graph('test_graph_00', ['channel', 'value'])
g.add_stat(sd.GraphYStat(['Entries', 'Y-Mean', 'Y-RMS'], ndigits=3))
for i in range(100):
    g.add_point(10*i, i**2/100 + i)
print(g)


h2 = sd.Histogram2d('test_histogram2d_00', 10, 0, 10, 10, 0, 10)
for i in range(1000):
    x = np.random.normal(5, 2)
    y = np.random.normal(5, 3)
    h2.fill(x, y)
print(h2)

