
from slowpy import SlowFetch
from slowpy import slowplot as plt


sf = SlowFetch('http://localhost:18881')
#sf.set_user(USER, PASS)                  # set the password if the SlowDash page is protected


channels = [ ch.name for ch in sf.channels() if ch.type in [ 'histogram', 'graph' ] ][0:4]
print(channels)

data = sf.data(
    channels = channels,           
    start = -3600,                        # Date-time string, UNIX time, or negative integer for seconds to "stop"
    stop = 0,                             # Date-time string, UNIX time, or non-positive integer for seconds to "now"
    resample = 0,                         # resampling time-backets intervals, zero for auto
    reducer = 'mean',                     # 'last' (None), 'mean', 'median'
    filler = None,                        # 'fillna' (None), 'last', 'linear': ### NOT YET IMPLEMENTED ###
)


# plot the last object in the time-series of objects
for ch, (t, x) in data.items():
    plt.plot(x[-1], label=ch)
plt.legend()

plt.show()
