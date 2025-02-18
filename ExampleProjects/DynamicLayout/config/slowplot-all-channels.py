import sys, os
from slowpy.control import ControlSystem

slowdash_url = os.environ.get('SLOWDASH_URL', None)
if slowdash_url is None:
    sys.stderr.write(f'unable to get SlowDash URL\n')
    sys.exit(-1)


sys.stderr.write(f'SlowDash URL: {slowdash_url}\n')
slowdash = ControlSystem().http(slowdash_url).slowdash()
channels = slowdash.channels().get()
sys.stderr.write(f'Channels: {channels}\n')


layout = {
    "panels": [{
        "type": "timeaxis",
        "plots": [{ "type": "timeseries", "channel": ch['name'] }]
    } for ch in channels if ch.get('type', 'numeric') == 'numeric' ]
}

print(layout)
