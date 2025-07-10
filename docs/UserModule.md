---
title: User Module
---

# Applications
The User Module is a Python module placed in a SlowDash project directory that can be used for:

- sending data to the web interface (tables, trees, etc.)
- dispatching commands from the web interface

And as advanced usage:

- dynamically creating HTML panels with data content
- dynamically creating SlowPlot panel layouts
- overriding SlowDash Web API to extend or modify it

SlowTask is an extension of the user module and should be suitable for most simple cases. The User Module is provided for full flexibility beyond SlowTask.

# Project Configuration File
```yaml
slowdash_project:
  name: ...
  module:
    file: FILE_PATH
    parameters:
        KEY1: VALUE1
        ...
    data_suffix: SUFFIX
    enabled_for_cgi: false
    enabled_for_commandline: true
```

[TODO] implement SUFFIX

By default, user modules are not enabled when the server program is launched via CGI. 
To enable this, set the `enabled_for_cgi` parameter to `true`. 
Be cautious of all potential side effects, including performance overhead and security risks. 
As multiple user modules can be loaded in parallel, splitting user functions between a CGI-enabled module and a disabled one might be a good strategy.

### Example
```yaml
slowdash_project:
  name: ...
  module:
    file: ./mymodule.py
```
- The `mymodule.py` file in the user project directory will be loaded into SlowDash.
- Callback functions in `mymodule.py` will be called in various contexts.


# User Module Structure
```python
### Called when this module is loaded. The params are the parameters from the configuration file.
def _initialize(params):
    ...

    
### Called during SlowDash termination.
def _finalize():
    ...

    
### Called when web clients need a list of available channels.
# Return a list of channel structs, e.g., [ { "name": NAME1, "type": TYPE1 }, ... ]
def _get_channels():
    ...
    return []


### Called when web clients request data.
# If the channel is not known, return None
# else return a JSON object of the data in the format described in the Data Model document.
def _get_data(channel):
    ...
    return None


### Called when web clients send a command.
# If the command is not recognized, return None
# elif command is executed successfully, return True
# else return False or { "status": "error", "message": ... }
def _process_command(doc):
    ...
    return None


### Called periodically while the system is running
# If this function is defined, a dedicated thread is created for it.
# Do not forget to insert a sleep, otherwise the system load becomes unnecessarily high.
def _loop():
    ...
    time.sleep(0.1)


### Instead of _loop(), a lower-level implementation with _run() and _halt() can also be used.
# _run() is called as a thread after _initialize(), and _halt() is called before _finalize().
is_stop_requested = False
def _run():
    global is_stop_requested
    while not is_stop_requested:
        ....
        time.sleep(0.1)

def _halt():
    global is_stop_requested
    is_stop_requested = True
```

[TODO] implement the full data-source interface


# Example User Data Source
This example can be found in `Examples/Advanced/UserModule`.

### Project Configuration File
```yaml
slowdash_project:
  name: WorldClock
  module:
    file: worldclock.py
    parameters:
        timeoffset: -9
    data_suffix: worldclock
```

### Python Module
```python
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
        return { 'tree': {
            'UnixWorldClock': t,
            'UTC': dt.astimezone(datetime.timezone.utc).isoformat(),
            'Local': dt.astimezone().isoformat(),
            '%+dh'%timeoffset: dt.astimezone(tz).isoformat()
        }}

    return None


# for testing
if __name__ == '__main__':
    print(_get_data(_get_channels()[0]['name']))
```

### Testing the Module
Running the `slowdash` command without the port number option displays the query result on screen. The query string is provided as the first argument.

The following two queries help test a data source module:

- `channels`: query for a channel list
- `data/CHANNEL`: query for data from the channel

```console
$ slowdash channels
[{ "name": "WorldClock", "type": "tree" }]

$ slowdash data/WorldClock --indent=4
{
    "WorldClock": {
        "start": 1678801863.0,
        "length": 3600.0,
        "t": 1678805463.0,
        "x": {
            "tree": {
                "UnixTime": 1678805463.7652955,
                "UTC": "2023-03-14T14:51:03.765296+00:00",
                "Local": "2023-03-14T15:51:03.765296+01:00",
                "-9h": "2023-03-14T05:51:03.765296-09:00"
            }
        }
    }
}
```

### Using it from a Web Browser
- Start `slowdash` in the project directory
- Add a new "Tree" panel with channel "WorldClock".

<img src="fig/UserModule-DataSource.png" style="width:70%;border:thin solid gray">


# Example User Command Dispatcher

Add the following function to the example user data source above:

### Python Module
```python
def _process_command(doc):
    global timeoffset
    try:
        if doc.get('set_time_offset', False):
            timeoffset = int(doc.get('time_offset', None))
            return True
    except Exception as e:
        return { "status": "error", "message": str(e) }

    return False

```

Create an HTML form to send commands from a web browser:
```html
<form>
  Time Offset (hours): <input type="number" name="time_offset" value="0">
  <input type="submit" name="set_time_offset" value="Set">
</form>
```
Save this in a file named `html-WorldClock.html` and place it in the `config` directory of the user project.
Restart `slowdash` and on the web layout, add a new "HTML/Form" panel with HTML named `WorldClock`.

<img src="fig/UserModule-Dispatcher.png" style="width:70%;border:thin solid gray">

When the `Set` button is clicked, the form data is sent to the user module as a JSON document. On the terminal screen, you will see a message like:
```
23-03-14 16:37:46 INFO: DISPATCH: {'set_time_offset': True, 'time_offset': '3'}
```

# User Module Threading
A dedicated thread is created for each user module, and the module is loaded within that thread. 
Therefore, all statements outside functions will be executed in this thread at the time of module loading, followed by `_initialize()`. 

If the `_loop()` function is defined in a user module, the function is called periodically within the user module thread:
```python
def _loop():
    do_my_task()
    time.sleep(0.1)
```

If the `_run()` function is defined, a dedicated thread is created, and the function will be started immediately after `_initialize()`. 
When `_run()` is used, a terminator function, `_halt()`, should also be defined in the user module to stop the thread. 
The `_halt()` function is called just before `_finalize()`. 
A typical construction of `_run()` and `_halt()` looks like:
```python
is_stop_requested = False

def _run():
    global is_stop_requested
    while not is_stop_requested:
        do_my_task()
        time.sleep(0.1)

def _halt():
    global is_stop_requested
    is_stop_requested = True    
```

If both `_run()` and `_loop()` are defined, `_run()` is called first (after `_initialize()`), followed by `_loop()` and `_finalize()`.

All other callback functions, such as `_process_command()`, `_get_channels()`, and `_get_data()`, are called from the main SlowDash thread (not the user module thread). 
Therefore, these can be called concurrently with the user thread callbacks (`_initialize()`, `_loop()`, `_run()`, etc.). 
It is okay to start another thread in user modules, as done in SlowTask which creates a dedicated thread for each `_process_command()` call.

# Tips
### Debug / Log Messages 
To print debug messages from user modules, use the logging module. Direct outputs to `logging` will be included in SlowDash logging. 
If you do not want this, define your own logger object:
```python
import logging
logger = logging.getLogger(name)
logger.addHandler(logging.StreamHandler(sys.stderr))
logger.setLevel(logging.INFO)

def _process_command(doc):
    logger.info(doc)
    ...
```

### User Task Class
To avoid using numerous "global" variables, consider creating a class to handle user tasks and using the user module interface functions to simply forward messages.
```python
class MyTask:
    ....

my_task = MyTask()

def _loop():
    my_task.do()
    time.sleep(0.1)
    
def _process_command(doc):
    return my_task.process_command(doc)    
```

### Standalone Mode
It is often convenient to have the user module executable in standalone mode. 
```python
if __name__ == '__main__':
    _initialize({})
    for i in range(10):
        _loop()
    _finalize()
```

For continuous execution, signals might be used to stop the thread:
```python
def stop(signum, frame):
    _halt()
    
if __name__ == '__main__':
    import signal
    signal.signal(signal.SIGINT, stop)
    _initialize({})
    _run()
    _finalize()
```

# Advanced Topics 
## Async User Functions
User Module functions can be either standard (`def`) or async (`async def`). 
As User Module functions are executed in a dedicated thread, using `await` in `async` functions will not significantly improve overall performance. 
However, this allows users to use async services as described below.

## Using SlowDash App Functions
To access services implemented in the SlowDash App, such as invoking Web API and publishing streaming data, the instance of the SlowDash App can be passed to the User Module if the `_setup(app)` function is defined:
```python
import asyncio

slowdash = None
def _setup(app):
    global slowdash
    slowdash = app

async def _loop():
    await slowdash.request_publish(topic='user_news', message='I am still alive')
    await asyncio.sleep(1)
```
If defined, `_setup(app)` is called before `_initialize(params)`. 
Optionally, `_setup()` can take a second argument, `params`, which is identical to the argument passed to `_initialize(params)`.

Note that most SlowDash App services are async and must be called with `await` in an `async` user function (or handle the return values properly, e.g., with `asyncio.gather()`).

## Dynamic Generation of HTML Content
HTML forms associated with a user module (`html-WorldClock.html` in the example above) can be created directly from the user module, eliminating the need for a separate HTML file in the `config` directory. 
For this, define the `_get_html()` callback function and return the HTML text:
```python
def _get_html():
    return f'''
        <form>
          Time Offset (hours): <input type="number" name="time_offset" value="0">
          <input type="submit" name="set_time_offset" value="Set">
        </form>
    '''
```
This will insert an HTML element as if a file named `html-UserModuleName.html` existed in the `config` directory.

When an HTML panel is placed on a layout, an "On Update" option is available, which includes a "reload HTML" checkbox. 
If this option is checked, the HTML content is reloaded with every data update, enabling a user module to generate dynamic data content.
The HTML does not have to be a form; it can be any valid HTML element. 
A table with live values would be a typical example of this kind of application.

To create multiple HTML forms, define the `_get_html_list()` callback function that returns a list of names. 
A name from the list will be passed to the `_get_html(name)` callback.
```python
def get_html_list():
    return ['settings', 'data_table']

def _get_html(name):
    if name == 'settings':
        return f'''<form> ... </form>'''
    elif name == 'data_table':
        return f'''<table> ... </table>'''
    else:
        return None
```

## Dynamic Generation of Panel Layouts
Similar to the dynamic generation of HTML forms, panel layouts (content of `config/slowplot-XXX.json` files) can be dynamically generated. 
To do this, define the `_get_layout()` callback function and return a JSON object describing the layout:
```python
def _get_layout():
    return {
        "meta": { "name": "worldclock", "title": "World Clock" },
        "control": {
            "grid": { "rows": 1, "columns": 2 }
        },
        "panels": [
            { "type": "tree", "channel": "WorldClock" },
            { "type": "html", "file": "worldclock" }
        ],
    }
```
This will insert a SlowPlot layout as if a file named `slowplot-UserModuleName.json` existed in the `config` directory.

In the same way as HTML forms, multiple layouts can be generated:
```python
def get_layout_list():
    return ['WorldClock', 'LocalClock']

def _get_layout(name):
    if name == 'WorldClock':
        return { ... }
    elif name == 'LocalClock':
        return { ... }
    else:
        return None
```

## Overriding SlowDash Web API
SlowDash uses the Slowlette Web framework, described in the [Web Server section](Slowlette.html), to handle Web API requests. 
If a Slowlette App instance is defined in a User Module, it will be integrated into the SlowDash Web API using the Slowlette aggregation mechanism. 
This feature can be used to add new APIs or modify existing APIs. 
Be extremely careful when using this because modifying APIs can easily disrupt the entire SlowDash behavior.

The examples here can be found in `ExampleProjects/Advanced/UserModuleSlowlette`.

### Channel & Data API Extension
Here is an example for enabling a User Module to respond to data requests with a time-range parameter. 
(Note that the `_get_data()` callback cannot do this, as it is designed to return "current" data.)
```python
import slowlette
webapi = slowlette.Slowlette()

@webapi.get('/api/channels')
def get_channels():
    return [ { 'name': 'data_query', 'type': 'tree' } ]

@webapi.get('/api/data/{channels}')
def get_data(channels:str, length:float=None, to:float=None, resample:float=None, reducer:str=None):
    if 'data_query' not in channels.split(','):
        return None
    
    record = { "data_query": { "x": {
        'tree': {
            'channels': channels,
            'length': length,
            'to': to,
            'resample': resample,
            'reducer': reducer,
        }
    }}}

    return record
```
Directly handling the Web API allows User Modules to perform any action for the request. 
Slowlette will distribute a web request to all possible (matching) handlers in the system and aggregate the multiple responses. 
The handler for `/channels` above returns only one channel, but the client (web browser) will receive the entire list of channels due to this aggregation mechanism. 

### Config List & Content API Extension
Here is another example for overriding SlowDash API more aggressively. 
In this example, the handler for `/config/contentlist` (a request to return a list of project `config` directory contents) inserts a slowplot file entry, `slowplot-PlotLayoutOverride.json`, which actually does not exist. 
Then the handler for the content request (`/config/content/FILENAME`) returns dynamically generated content (time-series plots for all channels, where the channel list is obtained from the SlowDash App in `_setup()`), as if the file existed in the `config` directory with that content. 
```python
import slowlette
webapi = slowlette.Slowlette()

channels = []
async def _setup(slowdash):
    global channels
    channels = await slowdash.request_channels()

    
@webapi.get('/api/config/contentlist')
def add_slowplot_PlotLayoutOverride():
    # this entry will be "injected" into the list through Slowlette's response aggregation
    entries = [{
        "type": "slowplot",
        "name": "PlotLayoutOverride",
        "config_file": "slowplot-PlotLayoutOverride.json",
        "description": "Dynamically generated by UserModule"
    }]

    return entries


@webapi.get('/api/config/content/slowplot-PlotLayoutOverride.json')
def generate_slowplot_PlotLayoutOverride(request:slowlette.Request):
    request.abort()   # stop propagation to avoid being handled by SlowDash (no aggregation)

    layout = {
        "panels": [{
            "type": "timeaxis",
            "plots": [{ "type": "timeseries", "channel": ch['name'] }]
        } for ch in channels if ch.get('type', 'numeric') == 'numeric' ]
    }

    return layout
```
