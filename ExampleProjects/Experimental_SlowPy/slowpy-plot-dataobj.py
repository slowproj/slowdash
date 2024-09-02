#! /usr/bin/env python3        


import slowpy as slp
from slowpy.control import RandomWalkDevice

device = RandomWalkDevice()
histogram = slp.Histogram('test_histogram_01', 20, -10, 10)
histogram2d = slp.Histogram2d('test_histogram2d_01', 50, 0, 10, 50, 0, 100)
graph = slp.Graph('test_graph_01', labels=['ch', 'value', 'error'])

histogram.add_stat(slp.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))
histogram.add_stat(slp.HistogramCountStat(-5.2, 5.2))
histogram.add_stat(slp.HistogramCountStat(0, 10))
graph.add_stat(slp.GraphYStat(['Entries', 'Y-Mean', 'Y-RMS'], ndigits=3))
histogram2d.add_stat(slp.Histogram2dBasicStat())


from slowpy import slowplot as plt
plt.set_datastore('SlowStore.db')
fig, axes = plt.subplots(2,2, figsize=(8,6))


import time
import numpy as np


def update():
    records = device.read()
    x = np.linspace(0, 10, 100)
    y = np.random.randn(100)
    
    graph.clear()
    for record in records:
        histogram.fill(record["value"])
        graph.add_point(record["channel"], record["value"], y_err=np.sqrt(np.abs(record["value"])))

    for i in range(1000):
        x = np.random.normal(5, 2)
        y = np.random.normal(7, 3)
        histogram2d.fill(x, y*y)

    axes[0].plot(histogram)
    axes[1].plot(graph)
    axes[2].plot(histogram2d)


    
def start():
    while True:
        update()
        time.sleep(1000)
    

if __name__ == '__main__':
    plt.set_recurrence(update, interval=2000)
    plt.show()
    plt.generate_slowdash_config()
