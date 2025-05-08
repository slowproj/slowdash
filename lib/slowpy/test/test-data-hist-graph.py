
import numpy as np
import slowpy as slp


h = slp.Histogram(100, 0, 10)
h.add_attr('color', 'red')
h.add_stat(slp.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))
h.add_stat(slp.HistogramCountStat(0, 10))
for i in range(1000):
    h.fill(np.random.normal(5, 2))
print(h)


g = slp.Graph(['channel', 'value'])
g.add_stat(slp.GraphYStat(['Entries', 'Y-Mean', 'Y-RMS'], ndigits=3))
for i in range(100):
    g.add_point(10*i, i**2/100 + i)
print(g)


h2 = slp.Histogram2d(10, 0, 10, 10, 0, 10)
for i in range(1000):
    x = np.random.normal(5, 2)
    y = np.random.normal(5, 3)
    h2.fill(x, y)
print(h2)

