
import numpy as np
import matplotlib.pyplot as plt
from slowpy.control import control_system as ctrl


# this function is called periodically by SlowDash (if used in SlowDash GUI)
async def _loop():
    x = np.linspace(0, 10, 100)
    y1 = np.random.normal(7, 3, len(x))
    y2 = np.random.normal(3, 5, len(x))
    ey1 = np.random.poisson(7, len(x))
    ey2 = np.random.poisson(3, len(x))

    fig, axes = plt.subplots(2, 2)

    axes[0,0].plot(x, y1, label='plot A')
    axes[0,0].plot(x, y2)
    axes[0,1].errorbar(x, y1, yerr=ey1, fmt='o', label='errorbar A')
    axes[0,1].errorbar(x, y2, yerr=ey2, fmt='s')
    axes[1,0].hist(y1, bins=np.linspace(-5, 15, 11), label='hist A')
    axes[1,0].hist(y2, bins=np.linspace(-5, 15, 11))
    axes[1,1].scatter(y1, y2, c='red', label='scatter A')
    axes[1,1].scatter(x, y1, c='blue')

    axes[0,0].set_title("plots")
    axes[0,1].set_title("errorbars")
    axes[1,0].set_title("histograms")
    axes[1,1].set_title("scatters")
    axes[0,1].set_xlim(-1, 11)
    axes[0,1].set_ylim(-25, 30)
    axes[0,0].set_xlabel("X")

    
    # If used from SlowDash (no GUI mode), this prints an error message but it should not be harmful.
    # Remove this line if this script will not be used stand-alone.
    plt.show()

    # This will create a SlowDash layout config (slowplot-XXX) and send the content data to SlowDash.
    await ctrl.aio_publish(fig, name='mpl')

    # If a figure is created in a loop, it must be closed every time.
    plt.close()

    # loop delay
    await ctrl.aio_sleep(0.5)


    
# for standalone running
if __name__ == '__main__':
    import asyncio
    asyncio.run(_loop())
