# worldclock.py

import time, datetime
timeoffset = 0


def _initialize(params):
    global timeoffset
    timeoffset = params.get('timeoffset', 0)

    
def _get_channels():
    return [
        {'name': 'WorldClock', 'type': 'tree'},
    ]


def _get_data(channel):
    if channel == 'WorldClock':
        t = time.time()
        dt = datetime.datetime.fromtimestamp(t)
        tz = datetime.timezone(datetime.timedelta(hours=timeoffset))
        return { 'tree': {
            'UnixTime': t,
            'UTC': dt.astimezone(datetime.timezone.utc).isoformat(),
            'Local': dt.astimezone().isoformat(),
            '%+dh'%timeoffset: dt.astimezone(tz).isoformat()
        }}

    return None


def _process_command(doc):
    global timeoffset
    try:
        if doc.get('set_time_offset', False):
            timeoffset = int(doc.get('time_offset', None))
            return True
    except Exception as e:
        return { "status": "error", "message": str(e) }

    return False



import slowlette
app = slowlette.Slowlette()
@app.get('/hello/{name}')
def hello(name:str='stranger'):
    return f"Hello {name}, I'm a WorldClock"



# for testing
if __name__ == '__main__':
    print(_get_data(_get_channels()[0]['name']))
