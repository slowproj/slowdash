
import numpy as np
import matplotlib.pyplot as plt
from slowpy.control import control_system as ctrl


async def _initialize():
    # This function is called only when this script is executed in SlowDash.
    # Here we disable Matplotlib GUI
    import matplotlib
    matplotlib.use("Agg")  # Anti-Grain Geometry: no GUI


async def _loop():
    x = np.linspace(0, 10, 2)
    y1 = 5*np.sin(x) + 7
    y2 = 6*np.cos(x) + 7
    dy = np.random.poisson(5, len(x))
    
    fig, [ax1, ax2] = plt.subplots(2, 1)
    ax1.plot(x, y1, label='plot A')
    ax1.plot(x, y2)
    ax2.hist(np.random.randn(100), bins=10, label='hist A')
    ax2.hist(np.random.randn(100) + 1.5, bins=10, label="hist B")
    ax1.errorbar(x, y1, yerr=dy, fmt='o', label='errorbar A')
    ax1.errorbar(x, y2, yerr=dy, fmt='s')
    ax1.scatter(y1, y2, c='red', label='scatter A')
    ax1.scatter(y2, x, c='blue')
    ax1.set_xlabel("X")
    ax2.set_title("histograms")
    ax1.set_xlim(-10, 20)
    ax2.set_ylim(0, 50)

    await ctrl.aio_publish(fig, name='mpl')

    # in Agg (No-GUI), this shows an error message but it should not be harmful
    plt.show()

    # if a figure is created in a loop, it must be closed every time
    plt.close()

    await ctrl.aio_sleep(0.5)

    
    
# for standalone testing
if __name__ == '__main__':
    import asyncio
    asyncio.run(_loop())
