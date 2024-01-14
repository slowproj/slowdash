#! /usr/bin/env python3        


import numpy as np
from slowpy import slowplot as plt
plt.set_datastore('SlowStore.db')

fig, axes = plt.subplots(2, 1)
fig.subplots_adjust(hspace=0.3)


def update():
    x = np.linspace(0, 10, 100)
    y = np.random.randn(100)
    axes[0].plot(x, y)
    axes[0].plot(x, x+y)
    axes[1].hist(y)
    axes[0].set_title("Graphs from Axes.plot()")
    axes[1].set_title("Histogram from Axes.hist()")


plt.set_recurrence(update, interval=2000)
plt.show()
plt.generate_slowdash_config()
