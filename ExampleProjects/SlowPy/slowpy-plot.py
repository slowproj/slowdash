#! /usr/bin/env python3        

import numpy as np
from slowpy import slowplot as plt
plt.set_datastore('SlowStore.db')

fig, axes = plt.subplots(2, 2)
fig.subplots_adjust(hspace=0.4)

x = np.linspace(0, 10, 100)
y = np.random.randn(100)


#axes[1].set_yscale('log')
axes[0].set_title("Graphs from Axes.plot()")
axes[1].set_title("Histogram from Axes.hist()")
axes[2].set_title("Axes.scatter()")
axes[3].set_title("Axes.hist2d()")


axes[0].plot(x, y, 'o', label="Graph 1")
axes[0].plot(x, x+y, 's', label="Graph 2")
axes[1].hist(y, label="Histogram")
axes[2].scatter(x, y, label="Scatter")
axes[3].hist2d(x, y, bins=30, label="Histogram2d")

#plt.legend()


plt.show()
plt.savefig("slowpy-plot.png")
plt.generate_slowdash_config()
