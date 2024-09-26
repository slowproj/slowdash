#! /usr/bin/env python3        

from slowpy import slowplot as plt
plt.set_datastore('sqlite:///SlowStore.db', table='SlowData')

fig, axes = plt.subplots(2,2, figsize=(8,6))
fig.subplots_adjust(hspace=0.4)


import numpy as np
def update():
    x = np.linspace(0, 10, 100)
    y = np.random.poisson(10, size=100)
    y2 = np.random.poisson(20, size=100)

    axes[0].plot(x, y, 'o', label="Graph 1")
    axes[0].plot(x, x+y2, 's', label="Graph 2")
    axes[1].hist(y, label="Histogram")
    axes[2].hist2d(y, y2, bins=30, label="Histogram2d")
    axes[3].scatter(y, y2, label="Scatter")

    axes[0].set_title("Graphs from Axes.plot()")
    axes[1].set_title("Histogram from Axes.hist()")
    axes[2].set_title("Histogram2d from Axes.hist2d()")
    axes[3].set_title("Graph from Axes.scatter()")

    #axes[1].set_yscale('log')

    

if __name__ == '__main__':
    plt.set_recurrence(update, interval=500)
    plt.show()
    plt.savefig("test-slowplot-plt.png")
    plt.generate_slowdash_config()
