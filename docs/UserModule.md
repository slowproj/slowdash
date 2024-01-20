---
title: User Module
---

# Applications
In Slow-Dash projects, user Python module can be used for:

- sending data to the web interface (table, tree, etc)
- dispatching "command" from the web interface

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
    cgi_enabled: False
```

[TODO] implement SUFFIX

By default, user modules are not enabled if the server program is launched by CGI. To enable this, set the `cgi_enabled` parameter `True`. Be careful for all the side effects, including performance overhead and security issues. As multiple user modules can be loaded in parallel, splitting functions to a CGI-enabled module and disabled one might be a good strategy.

### Example
```yaml
slowdash_project:
  name: ...
  module:
    file: ./mymodule.py
```
- `mymodule.py` at the user project directory will be loaded to slow-dash.
- Call-back functions in `mudule.py` will be called for various context.


# User Module structure
```python
### Called when this module is loaded. The params are the parameters in the configuration file.
def initialize(params):
    ...

    
### Called during termination of slow-dash.
def finalize():
    ...

    
### Called when web clients need a list of available channels.
# Return a list of channel struct, e.g.,  [ { "name": NAME1, "type": TYPE1 }, ... ]
def get_channels():
    ...
    return []


### Called when web clients request data.
# If the channel is not known, return None
# else return a JSON object of the data, in the format described in the Data Model document.
def get_data(channel):
    ...
    return None


### Called when web clients send a command.
# If command is not recognized, return None
# elif command is executed successfully, return True
# else return False or { "status": "error", "message": ... }
def process_command(doc):
    ...
    return None


### Called periodically while the system is running
# If this function is defined, a dedicated thread is created for that.
# Do not forget to insert a sleep otherwise the system load becomes unnecessarily large.
def loop():
    ...
    time.sleep(0.1)


### Instead of loop(), a lower level implementation with run() and halt() can also be used.
# run() is called as a thread after initialize(), and halt() is called before finalize().
is_stop_requested = False
def run():
    global is_stop_requested
    while not is_stop_requested:
        ....
        time.sleep(0.1)
def halt():
    global is_stop_requested
    is_stop_requested = True
```

[TODO] implement the full data-source interface


# Example User Data Source
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

def initialize(params):
    global timeoffset
    timeoffset = params.get('timeoffset', 0)

    
def get_channels():
    return [
        {'name': 'WorldClock', 'type': 'tree'},
    ]


def get_data(channel):
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
    print(get_data(get_channels()[0]['name']))
```

### Testing the module
Running the `slowdash` command without a port number option shows the query result to screen. The query string is given as the first argument.

Two queries are useful to test the module:

- `channel`: query for a channel list
- `data/CHANNEL`: query for data for the channel

```console
$ slowdash channels
[{ "name": "WorldClock", "type": "tree" }]

$ slowdash data/WorldClock
{ "WorldClock": { "start": 1678801863.0, "length": 3600.0, "t": 1678805463.0, "x": { "tree": {
    "UnixTime": 1678805463.7652955,
    "UTC": "2023-03-14T14:51:03.765296+00:00",
    "Local": "2023-03-14T15:51:03.765296+01:00",
    "-9h": "2023-03-14T05:51:03.765296-09:00"
}}}}
```
(the output above is reformatted for better readability)


### Using it from web browser
- Start slow-dash at the project directory
- Add a new  "Tree" panel, with channel "WorldClock".

<img src="fig/UserModule-DataSource.png" style="width:70%;border:thin solid gray">


# Example User Command Dispatcher

To the example user data source above, add the following function:

### Python Module
```python
def process_command(doc):
    global timeoffset
    try:
        if doc.get('set_time_offset', False):
            timeoffset = int(doc.get('time_offset', None))
            return True
    except Exception as e:
        return { "status": "error", "message": str(e) }

    return False

```

Make a HTML form to send commands from Web browser:
```html
<form>
  Time Offset (hours): <input type="number" name="time_offset" value="0">
  <input type="submit" name="set_time_offset" value="Set">
</form>
```
Save the file at the `config` directory under the user project direcotry.
Add a new HTML panel with HTML file `WorldClock`.

<img src="fig/UserModule-Dispatcher.png" style="width:70%;border:thin solid gray">

When the `Set` button is clicked, the form data is sent to the user module as a JSON document. On the terminal screen where the slowdash command is running, you can see a message like:
```
POST: /slowdash.cgi/control
23-03-14 16:37:46 INFO: DISPATCH: {'set_time_offset': True, 'time_offset': '3'}
```

# User Module Threading
If the `loop()` function is defined in a user module, a dedicated thread is created and the function is called periodically:
```python
def loop():
    do_my_task()
    time.sleep(0.1)
```

Instead of using `loop()`, if the `run()` function is defined, a dedicated thread is created and the function will be started immediately after `initialize()`. When `run()` is used, a terminator function, `halt()` must be also defined in the user module to stop the thread. The `halt()` function is called just before `finalize()` is called. A typical construction of `run()` and `halt()` looks like:
```python
is_stop_requested = False

def run():
    global is_stop_requested
    while not is_stop_requested:
        do_my_task()
        time.sleep(0.1)

def halt():
    global is_stop_requested
    is_stop_requested = True    
```

It is okay to implement threading within the user module. Just avoid using the reserved function names (`run()` etc.)
```python
import threading
current_thread = None
is_stop_requested = False

def main():
    global is_stop_requested
    while not is_stop_requested:
        do_my_task()
        time.sleep(0.1)

def initialize(params):
    global current_thread
    current_thread = threading.Thread(target=main)
    current_thread.start()
    
def finalize():
    global current_thread, is_stop_requested
    is_stop_requested = True
    if current_thread is not None:
        current_thread.join()
```

# Tips
### Debug / Log Messages 
 To print debug messages from user modules, use the logging module:
```python
import logging
logger = logging.getLogger(name)
logger.addHandler(logging.StreamHandler(sys.stderr))
logger.setLevel(logging.INFO)

def process_command(doc):
    logger.info(doc)
    ...
```

### User Task Class
To avoid using a number of "global" variables, consider making a class to handle user tasks and using the user module interface functions for simply forwarding the messages.
```python
class MyTask:
    ....

my_task = MyTask()

def loop():
    my_task.do()
    time.sleep(0.1)
    
def process_command(doc):
    return my_task.process_command(doc)    
```

### Standalone Mode
It is often convenient to have the user module executable standalone. For single execution of a user task, just call `loop()` once:
```python
if __name__ == '__main__':
    initialize({})
    loop()
    finalize()
```

For contineous execution, signal might be used to stop the loop:
```python
def stop(signum, frame):
    halt()
    
if __name__ == '__main__':
    import signal
    signal.signal(signal.SIGINT, stop)
    initialize({})
    run()
```
