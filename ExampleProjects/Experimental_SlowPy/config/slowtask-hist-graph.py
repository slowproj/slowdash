#! /usr/bin/env python3        

import slowpy as slp
graph = slp.Graph(labels=['ch', 'value', 'error'])
histogram = slp.Histogram(30, 0, 30)
histogram2d = slp.Histogram2d(20, 0, 30, 20, 0, 50)

graph.add_stat(slp.GraphYStat(['Entries', 'Y-Mean', 'Y-RMS'], ndigits=3))
histogram.add_stat(slp.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))
histogram.add_stat(slp.HistogramCountStat(-5.2, 5.2))
histogram.add_stat(slp.HistogramCountStat(0, 10))
histogram2d.add_stat(slp.Histogram2dBasicStat())


from slowpy import slowplot as plt
plt.set_datastore('sqlite:///SlowStore.db', table='SlowData')

fig, axes = plt.subplots(2,2, figsize=(8,6))
fig.subplots_adjust(hspace=0.4)


import numpy as np
def update():
    x = np.linspace(0, 10, 100)
    y = np.random.poisson(10, size=100)
    y2 = np.random.poisson(20, size=100)
    
    graph.clear()
    graph.add_point(x=x, y=y, y_err=np.sqrt(y))
    histogram.fill(y)
    histogram2d.fill(y, y2)

    axes[0].plot(graph, label='Graph 1')
    axes[1].plot(histogram, label='Histogram 1')
    axes[2].plot(histogram2d, label='Histogram2d 1')

    axes[0].set_title("Graphs from Graph object")
    axes[1].set_title("Histogram from Histogram object")
    axes[2].set_title("Histogram2d from Histogram2d object")

    #axes[1].set_yscale('log')

    
    
# for execusion as a SlowTask    
import time
def _loop():
    update()
    time.sleep(500)
    

# for standalone execusion
if __name__ == '__main__':
    plt.set_recurrence(update, interval=500)
    plt.show()
    plt.savefig("test-slowplot-hist-graph.png")
    plt.generate_slowdash_config()
