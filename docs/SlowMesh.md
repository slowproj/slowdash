---
title: SlowMesh and SlowTask
---

# Overview
SlowDash is a distributed parallel system in which multiple SlowTasks work cooperatively under a SlowDash server.
SlowMesh is the messaging and communication infrastructure between the SlowDash server and SlowTasks.
A SlowTask is typically a single Python script; some are written by users, while others are provided in libraries of reusable tasks.
SlowTasks use the SlowPy library to access SlowMesh communication and other functions available on the mesh.

<img src="fig/SlowMeshConcept.png" width="40%">
<img src="fig/SlowMesh-SlowTask.png" width="40%">

## SlowMesh
SlowMesh is the communication infrastructure that allows SlowDash components (the SlowDash server and various SlowTasks) to work cooperatively.
It uses a messaging backbone as the lower communication layer and provides PubSub, RPC, and Registry (Key-Value Store) functions on top of it.
In addition to the built-in SlowMQ provided by SlowDash, widely used external systems such as NATS, MQTT, Redis, and RabbitMQ can be used directly as the messaging backbone.

SlowMesh provides the following three communication mechanisms.

- **PubSub**: A thin, unified wrapper around the messaging-backbone interfaces implemented in SlowPy Control
- **Remote Procedure Call (RPC)**: Remote function calls built on top of PubSub
- **Registry (Key-Value Store)**: A shared namespace implemented using RPC

## SlowTask
A SlowTask is an execution unit that runs independently yet cooperatively on SlowMesh (roughly, one Python script).
It can start and stop together with the SlowDash server, or it can start and stop independently on its own schedule.
It can also run on a PC different from the SlowDash server.

SlowTask provides the following functions.

- Calling user functions at startup, shutdown, specified times, or fixed time intervals
- Communication through SlowMesh (exporting functions, sending data, etc.)
- Communication with the SlowDash server over HTTP (for example, obtaining initial configuration information)



# SlowMesh
## Components
### SlowPy Mesh Library
This library is used from SlowTask scripts.

- Mesh (`slowpy.mesh.mesh.py`): Interface to SlowMesh communication functions
- Tasklet (`slowpy.mesh.tasklet.py`): Adapter for running a Python script as an independent task (SlowTask) on SlowMesh
- MeshStdio (`slowpy.mesh.stdio.py`): Bridge that redirects the standard input/output of a Python script to Mesh PubSub
- MeshPakcet (`slowpy.mesh.packet.py`): Serialization and deserialization of messages exchanged through SlowMesh


### SlowDash Mesh Services
These provide SlowMesh-related services inside the SlowDash server.

- Registry (Key-Value Store) service
- PubSub Last-Value Cache (subscribes to all PubSub topics and stores received data in the Registry)
- WebMesh API: publish using HTTP POST and subscribe using Server-Sent Events (SSE)
- TODO: Control History (subscribe to the PubSub `control.>` and `sd.rpc.>` topics and store received data in a database)

### SlowMQ Backbone
SlowMQ is the PubSub broker built into SlowDash. Because it is included in the SlowDash server process, it can be used as-is without any additional configuration.
It is implemented using WebSockets.


## PubSub
### Example
Typically, SlowMesh is constructed by the Tasklet described later.

##### Publish
```python
topic = 'data.store.temp0'
data = { 'temp0': { 't': t, 'x': temp0 } }
await tasklet.mesh.aio_publish(topic, data)
```

##### Subscribe
```python
@tasklet.mesh.on('data.store.>')  # Specify a callback to be invoked when a message is received
async def handle_data(headers, data):
    topic = headers.get('topic')
    ...
```

### Backbone Connection
SlowPy Mesh PubSub is a thin wrapper around the messaging-backbone interfaces implemented in SlowPy Control.
The following messaging systems available in SlowPy Control can be selected:

| Backbone | SlowPy Module | Broker | Notes |
|---|---|---|---|
| SlowMQ | control-AsyncSlowMQ.py | Not required (built into SlowDash) | HTTP(S)-based and accessible across firewalls |
| NATS | control-AsyncNATS.py | A separate NATS Broker is required | |
| MQTT | control-AsyncMQTT.py | A separate MQTT Broker (such as eclipse-mosquitto) is required | 
| RabbitMQ | control-AsyncRabbitMQ.py | A separate RabbitMQ Broker is required | |
| Redis-PubSub | control-AsyncRedis.py | A separate Redis server is required | Topic filters have limitations |

The backbone service to use is specified by the URL passed to the Mesh constructor (or the `connect()` function):

| Backbone | URL Format |
|---|---|
| SlowMQ (WebSockets over HTTP or HTTPS)| `slowmq://HOST:PORT` (HTTP) or `slowmqs://HOST:PORT` (HTTPS) |
| NATS | `nats://HOST` |
| MQTT |  `mqtt://HOST` |
| RabbitMQ |  `rabbitmq://USER:PASS@HOST/EXCHANGE` |
| Redis-PubSub |  `redis://HOST/DB` |

If authentication information is required, insert `USER:PASS@` immediately before `HOST`.

For QoS settings (at-most-once / at-least-once / exactly-one), the basic assumption is to use the backbone defaults and configure the backbone directly when necessary. (At present, this part is not fully worked out.) The intended operational model is to switch backbones as the system grows, including for performance reasons—for example, starting with SlowMQ or Redis and moving to NATS when more performance or functionality is needed.

### Topic Filters
Filters modeled after NATS can be used.

- The hierarchy separator is `.`
- `*` matches any single hierarchy level
- `>` matches any number of trailing hierarchy levels (it can only be used as the final character)

When a backbone other than SlowMQ or NATS is used, these special characters are converted before being passed to the library. With Redis, which does not use a strict hierarchy, filter behavior may differ.

| Backbone  | Hierarchy Separator | One-Level Match | Any Number of Trailing Levels | Example 1 | Example 2 |
|--------------|--------------|------------|--------------------|---|--|
| (original characters) | `.` | `*` | `>` | `data.store.>` | `data.*.HV.ch100` |
| SlowMQ       | `.`          | `*`        | `>`                | `data.store.>` | `data.*.HV.ch100` |
| NATS         | `.`          | `*`        | `>`                | `data.store.>` | `data.*.HV.ch100` |
| MQTT         | `/`          | `+`        | `#`                | `data/store/#` | `data/+/HV/ch100` |
| RabbitMQ     | `.`          | `*`        | `#`                | `data.store.#` | `data.*.HV.ch100` |
| Redis-PubSub | `:`          | `*` (approximate behavior) | `*` (approximate behavior) | `data:store:*` | `data:*:HV:ch100` |

Including characters such as `/`, `#`, `+`, or `:` in topic names can cause problems when using a backbone for which those characters are special.
It is better to avoid using these characters.
(In principle they could be escaped, but that would require processing for every message; considering the usefulness and performance impact, escaping is unlikely to be implemented in the future.)

The assignment of these characters can be changed with Mesh constructor options, but because doing so also affects other parts that use Mesh (including user scripts), it is generally safer not to change them.

### MeshPacket
For some topics for which a message Schema is defined, a MeshPacket can be used to read and write data conforming to the prescribed schema.
Reading and writing message contents through MeshPacket is convenient because user scripts do not need to depend on the details of the Schema, and it saves the work of constructing and decoding messages.

MeshPacket is defined in `slowpy/mesh/packet`.
The following MeshPackets are currently available.

| Topic | MeshPacket Constructor |
|---|----|
|`data.*.>` | `DataPacket(values, *, tag:str|None=None, timestamp:float|None=None)` |
|`control.>` | `ControlPacket()` TODO: not implemented |

#### Example for Data Topics
The following example uses `mesh.DataPacket`, the MeshPacket for `data.>` topics. Data sent on this topic uses the SlowDash format described in [Data Model](DataModel.html). It is slightly complex, as follows:
```python
{
    channel: {
       "start": t0,      # Time origin (optional)
       "t": time,        # Array for TimeSeries data
       "x": value        # Array for TimeSeries data
    },
    ...                  # Other channels
}
```

##### Publish
```python
from slowpy.mesh import DataPacket

topic = 'data.store'
temp0 = thermometer.ch(0).get()
await tasklet.mesh.aio_publish(topic, DataPacket(temp0, tag='temp0'))  # Published under topic name data.store.temp0
```
Here, the constructor parameters of `DataPacket` are the same as those of `DataStore.append()`.
In other words, writing directly to the data store and publishing through SlowMesh use almost the same syntax.


##### Subscribe
```python
from slowpy.mesh import DataPacket

@tasklet.mesh.on('data.>')  # Specify a callback to be invoked when a message is received
async def handle_data(data:DataPacket):
    t = data.timestamp
    for ch, value in data.values.items():
        ...
```

DataPacket defines properties with the same names as its constructor parameters.


## Remote Procedure Call (RPC)
RPC is a mechanism for calling, by name, a Python function exposed by one SlowTask from another SlowTask.
It is implemented using the `sd.rpc`/`sd.rpc_reply` topics on PubSub.
The caller specifies its own reply topic, `sd.rpc_reply.{MeshID}`, in `reply_to` and publishes a request to `sd.rpc.{module_name}`. The executing side publishes reply data to the topic specified by `reply_to` in the request.

- Executing side: export a function with the `@mesh.export` decorator
- Calling side: call it with `mesh.aio_call(name, *args, **kwargs)`

### Example
##### Executing Side
```python
@tasklet.mesh.export
async def chat(line, *, sender=None):
    print(f'You ("{sender}") sent me "{line}".')
    print(f'I will send you the current time.')
    return str(datetime.datetime.now())
```

- At present, only JSON-serializable values can be returned as return values.
- RPC functions should return within about 1 second at most. The caller times out after 5 seconds by default.
- Long-running operations should be placed in a queue or executed as an asynchronous task, thread, etc.

##### Calling Side
```python
    return_value = await tasklet.mesh.aio_call('test-mesh-rpc.chat', line, sender='me')
```

- The first argument is `module_name.function_name`; subsequent arguments are passed directly as arguments to the remote function.
- At present, only JSON-serializable values can be passed as arguments.
- If an error occurs, an Exception is raised.
- The default timeout can be specified as a Mesh constructor parameter. Alternatively, `aio_call_many()` can be used to specify an individual timeout for each call.

##### Advanced Example
If multiple Tasks have the same name, one RPC call may receive multiple responses.
In this case, `aio_call()` returns only the first response and displays a warning if later responses are received.
To receive all responses, use `aio_call_many()` instead of `aio_call()`.
If the number of tasks is specified in `expected_replies`, the function waits for responses from all tasks and then returns a list of replies.
```python
    async def aio_call_many(self, name:str, args:list, kwargs:dict, *, expected_replies:int|None=None, timeout:float|None=None, raise_on_timeout:bool=False)
```
Each reply is a dict containing fields such as:
```python
 { 'status': 'ok', 'message': 'ok', 'return_value': result }
```
In addition to `ok`, `status` can be `error` or `cancelled`; in an error case, `message` contains the error message.
(TODO: include mesh_id and correlation_id in the reply)

`aio_call()` simply calls `aio_call_many()` with `expected_replies` set to `1` and `raise_on_timeout` set to `True`.

### Exporting a ControlNode
Remote access to a ControlNode is also implemented using RPC.

##### Executing Side
```python
from slowpy.control import ControlNode

class MyNode(ControlNode):
    def aio_set(self, value):
        ...
    def aio_get(self):
        return ...
    
tasklet.mesh.export(node_name, MyNode())
```

##### Calling Side
```python
    node = tasklet.mesh.remote_node(f'{module_name}.{node_name}')
    await node.aio_set(value)
    print(await node.aio_get())
```


## Registry (Key-Value Store)
Registry is a named value store shared by multiple SlowTasks. It is intended for sharing state, configuration values, processing requests, and similar information between processes.
It is implemented using RPC to the `sd_mesh_registry.py` module.

The Registry is accessed through the `registry` instance of the `Registry` class held by Mesh:
```python
    registry = tasklet.mesh.registry

    # Set a value
    await registry.aio_set('setup.run.number', run_number)
    
    # Get a value
    run_number = await registry.aio_get('setup.run.status')
```


Registry provides the following methods:

- Write (set): `async def aio_set(self, key, value, *, cas_revision:int|None=None) -> int|None`
- Read (get): `async def aio_get(self, key:str, default:Any=None, *, with_meta:bool=False) -> Any`
- List keys (keys): `async def aio_keys(self, prefix:str='', limit:int|None=1000)->list[str]`
- Delete (delete): `async def aio_delete(self, key:str, *, cas_revision:int|None=None) -> bool`

**Hierarchy**:
Keys have a hierarchical structure separated by a hierarchy separator (default: `.`). The separator can be changed, but it is generally safer not to change it.

**Key**:
Except for the hierarchy separator, use names similar to identifiers (variable names, etc.) in Python, C++, and similar languages. Specifically, names may contain only alphanumeric characters or underscores, and the first character may not be a digit.

**Value**:
At present, only JSON-serializable values can be used as Values. (TODO: support blobs such as images?)

**Grouping**:
By appending the `>` character to the end of a Key, entries below the specified hierarchy can be handled together as a single dict.


```python
    registry = tasklet.mesh.registry
    
    await registry.aio_set('user', 'slowuser')
    await registry.aio_set('state.run.mode', 'physics')
    await registry.aio_set('state.run.number', 123)
    await registry.aio_set('state.run', 'running')    # Note: this is not a very good example; 'state.run.status' would be better

    print(await registry.aio_keys('state.run'))       # -->  ['state.run.mode', 'state.run.number', 'state.run']
    print(await registry.aio_get('state.run.mode'))   # -->  physics
    print(await registry.aio_get('state.run'))        # -->  running
    print(await registry.aio_get('state.run.>'))      # -->  {'mode': 'physics', 'number': 123, '$value': 'running'}
    print(await registry.aio_get('.>'))               # -->  {'user': 'slowuser', 'state': {'run': {'mode': 'physics', 'number': 123, '$value': 'running'}}}
```

As shown in the last two examples, appending `>` to the end of `key` in `Registry.aio_get(key)` returns all nodes below that hierarchy together as a dict.
If, as with `state.run` in this example, a key has both an assigned value and child levels below it, it cannot naturally be converted directly into a dict or JSON (because one node cannot simultaneously be a value and have child nodes). In such a case, the value is stored in the `$value` field.
In general, it is safer to avoid this situation (do not store a value at a node that has child nodes). In the example above, changing `registry.set('state.run', 'running')` to something such as `registry.set('state.run.status', 'running')` avoids the issue.

Like `aio_get`, if `Registry.aio_set(key, value)` is called with `>` appended to the end of `key` and a dict is passed as `value`, nodes are created by expanding the dict below that hierarchy. In other words, the following two forms behave the same way.
```python
    doc = {'run': {'mode': 'physics', 'number': 123 }, 'running': True }
    await registry.aio_set('state>', doc)
```
```python
    await registry.aio_set('state.run.mode', 'physics')
    await registry.aio_set('state.run.number', 123)
    await registry.aio_set('state.running', True)
```
(`>` is ignored if the value is not a dict.)

Note that this differs from the following. Here, the entire object is stored as one dict value in a single node.
```python
    doc = {'run': {'mode': 'physics', 'number': 123 }, 'running': True }
    await registry.aio_set('state', doc)
```
In both cases, `aio_get('state.>')` returns the same result, but `aio_get('state.run.number')` behaves differently: in the latter case it returns None or the default value because no such node exists. Also, if the two styles are mixed, the value written as a dict is placed in the `$value` field. (Usually, expanding and storing with `>` causes fewer problems, but unexpanded storage as in the latter form is needed when recording dicts that contain arrays, for example. It is also needed when the original data is itself a dict, as with the PubSub Cache described later.)

Registry provides a Compare-And-Set (CAS) option to prevent unintentionally overwriting values written by others.

- Registry-value metadata is assigned a CAS Revision that counts writes
- `aio_set()` increments the CAS Revision and returns the new CAS Revision
- If the `cas_revision` option passed to `aio_set()` is not None, the write fails unless it matches the CAS Revision of the currently stored value
  - This prevents you from unknowingly overwriting a value you set if somebody else has modified it in the meantime
- `aio_delete()` works similarly. Deletion fails if the CAS Revision does not match

If the `with_meta` option of `aio_get()` is set to `True`, Meta Data including the write time and CAS Revision is returned:
```python
{
    "key": key,
    "value": value,
    "revision": CAS Revision,
    "updated": last write time
}
```

Values stored in the Registry can also be accessed through the WebAPI. See the HTTP API section below for details.
```console
$ curl "http://localhost:18881/api/registry/value?key=state.run"
{"$value": "running", "mode": "physics", "number": 123}
```

They can also be read in the same format as data in the database (using the same Web API and the same return-value format).
Specify `@registry:{key}` as the channel name.
```console
$ curl "http://localhost:18881/api/data/@registry:state.run"
{
    "@registry:state.run": {
        "start": 1781858837.4758086,
        "t": 3600.0,
        "x": {"tree": {"$value": "running", "mode": "physics", "number": 123}}
    }
}
```

### PubSub Last-Value Cache
The Registry service (`sd-mesh-registry.py`) implements the PubSub Last-Value Cache by subscribing to all PubSub topics (or selected topics) and retaining their contents. This allows Tasks that connect later to access status information and other data that were published before they connected.
TODO: In addition, by periodically saving these contents, the context could be restored after recovery from a SlowDash server crash.

By default, the PubSub Cache is stored in the Registry under `pubsub.{topic_name}`.

For example, suppose the Registry contains the following:

```json
{
  "pubsub.sd.task.spec.test_mesh_slowtask": {
    "mesh_id": "test_mesh_slowtask_vs13_158097_1",
    "name": "test_mesh_slowtask",
    "functions": [ { "name": "start" }, { "name": "display" } ],
    "variables": []
  },
  "pubsub.sd.task.heartbeat.test_mesh_slowtask": {},
  "pubsub.sd.task.spec.store": {
    "mesh_id": "store_vs13_214629_1",
    "name": "store",
    "functions": [],
    "variables": []
  },
  "pubsub.sd.task.heartbeat.store": {},
  ...
```

- Getting `pubsub.sd.task.spec.test_mesh_slowtask.>` retrieves the Spec for that task as a single dict / JSON object.
- Getting `pubsub.sd.task.heartbeat.>` retrieves the Heartbeats for all tasks as a single dict / JSON object.

(Be sure not to forget the final `>` when you want the result, including sub-branches, as a dict/JSON object.)


### Persistency
By marking a specified Registry path as persistent, every write to that path or any path below it causes the entire persistent subtree to be saved to a file. The generated filename is `registry-{path}.json`. The file is written in JSON format as flat one-entry-per-key records of the form `{subpath}: {record}`. (It is not converted into a tree using `{path}.>` because the flat form preserves entries whose values are themselves dicts.) The stored Registry values are automatically loaded the next time the Registry server (the SlowDash server) starts.

TODO: At present, metadata other than the value, such as CAS information, is saved but is not restored when loading.

TODO: At present, the list of Paths made persistent is hard-coded in `self._persistent_nodes` of the `Registry` class as follows.

- `pubsub.form.inputs.`

Note: Using `/` as the Registry separator causes serious trouble here.
The filename is escaped correctly, but the result is ugly.


## Standard Input/Output Redirection (MeshStdio)
With MeshStdio, standard output such as output from `print()` is also published to SlowMesh, and standard input such as `input()` can also be obtained from a subscription.
This allows SlowTask standard input/output to be read and written through PubSub.
A possible use is to provide a SlowTask console in the Web UI.

```python
    from mesh.stdio import MeshStdio
    mesh_stdio = MeshStdio(self._mesh, topic_prefix='sd.task')
    
    await mesh_stdio.aio_start()
    # During this period, print() is published and input() can be obtained from a subscription
    await mesh_stdio.aio_stop()
    
```
Messages written by `print()` or to `sys.stdio` / `sys.stderr` are published to the specified SlowMesh topic and are also written to the local standard output (or standard error). Similarly, requests to read from `input()` or `stdin` may receive input either from a SlowMesh subscription or from local standard input (whichever arrives first).

The PubSub topic name is `{prefix}.{stream}.{mesh_id}`. For example, if the Prefix is `sd.task`, the standard-output (stdout) topic is `sd.task.stdout.{task_name}.{mesh_id}`.

Multiple MeshStdio instances can be created and started on separate threads. In that case, input/output is routed according to thread ID.
(Output from `print()` on the thread that started a MeshStdio instance is routed to that MeshStdio instance.)
When SlowTasks are used as dynamically loaded modules, multiple SlowTasks run inside the SlowDash server process. In this case, each SlowTask runs on a separate thread, so each can have its own MeshStdio.

Because input/output channels are associated with thread IDs, if a SlowTask starts a new thread, MeshStdio must be explicitly attached to that thread and explicitly detached before the thread exits.
```python
def thread_run():
    mesh_stdio.attach_current_thread()
    # ...
    mesh_stdio.detach_current_thread()
```

When multiple MeshStdio instances are running across multiple threads in this way, there is ambiguity as to which thread should receive input from local `input()`.
MeshStdio handles this according to the following rules:

- If only one MeshStdio instance is running, local `input()` is delivered to it
- If, when local input arrives, there is already a thread waiting in `input()`, the input is delivered to that thread. If multiple threads are waiting, it is delivered to the thread that most recently began waiting for input
- Otherwise (multiple MeshStdio instances are running, but none is waiting in `input()`), the input is discarded

Note that these rules apply only to local `input()`. Input from SlowMesh PubSub has an explicit destination and is always routed appropriately.
The behavior described here concerns the case where multiple MeshStdio instances exist in one process and local input is provided to them.

## HTTP Bridge (WebMesh)
WebMesh is part of the SlowDash server process and allows Publish / Subscribe operations on SlowMesh to be performed over HTTP.
Publish is implemented using ordinary POST requests, while Subscribe is implemented using Server-Sent Events (SSE).
At present, only some topics, such as `data.*.`, can be subscribed to.

### Subscribe
To subscribe, first establish an SSE connection to `event/webmesh/attach` and obtain a client ID from the `register` event delivered over SSE.

```javascript
    let sse = new EventSource('http://localhost:18881/event/webmesh/attach');
    let client_id = null;
    sse.addEventListener("register", (event) => {
        client_id = JSON.parse(event.data).client_id;
    }
```

Then use this client ID to subscribe to a topic.
```javascript
    fetch('http://localhost:18881/api/webmesh/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
        body: JSON.stringify({
           'client_id': client_id,
           'topic': 'data.*.HV.ch0.V',
        })
    });
```

Data is sent to the browser as `message` events.
```javascript
    sse.addEventListener("message", (event) => {
        const message = JSON.parse(event.data);
        const headers = message.headers;
        const body = message.body;
        ...
    });
```

The currently implemented subscribable topics are listed below.
At present, SlowMesh PubSub topic filters cannot be used in topic names specified for streaming.
Use `*` and `>` literally as shown in the topic names below, and replace the `{channel}` portion as appropriate.

- `data.*.{channel}`
- `form.inputs.{form_name}`
- `sd.task.life_event.>`
- `sd.task.heartbeat.>`
- `sd.task.stdout.>`


### Publish
To Publish, simply POST to `api/webmesh/publish/{topic}`.
```javascript
    const topic = 'control.start';
    const message = {
       'run_number': 10,
       'length': 3600,
    };
    fetch('http://localhost:18881/api/webmesh/publish/' + encodeURIComponent(topic), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
        body: JSON.stringify(message),
    });
```


# SlowTask
A SlowTask is an execution unit that runs independently yet cooperatively on SlowMesh (roughly, one Python script).
It runs as a separate process and can either be managed from the SlowDash server or run independently of the SlowDash server.

## Creating and Running SlowTasks
### Script
To use a Python script as a SlowTask, include the Tasklet execution adapter.
(Alternatively, with some functional limitations, an unmodified plain Python script can also be run directly from SlowDash.)

```python
from slowpy.mesh import Tasklet
tasklet = Tasklet()

...(main body)...

# If you want to run the script standalone
if __name__ == '__main__':
    tasklet.run(mesh_url='slowmq://localhost:18881')
```

SlowTask as a whole runs concurrently using single-threaded asynchronous calls, so **using `time.sleep()` in the script freezes the entire task**.
The intended style is to use `@tasklet.loop(interval)` as described below so that explicit sleeps are not needed.
If a sleep is absolutely necessary, use `await asyncio.sleep()` or `await control_system.aio_sleep()`.


### Running
If a SlowTask script file is placed under the SlowDash project's `config` directory with the filename `slowtask-{name}.py`, the SlowDash server recognizes it and can start and stop it.

In addition, if a `task(s)` entry is created in `SlowdashProject.yaml` and `auto_start` is set, the SlowTask can automatically start when the SlowDash server starts.
```yaml
  tasks:
    - name: {name}
      auto_start: true
```

To run a SlowTask as a process independent of the SlowDash server, normally use the `slowdash-task` command.
```console
$ slowdash-task  slowtask-mytask.py --mesh=slowmq://localhost:18881
```

If the script contains `if __name__ == '__main__': tasklet.run()`, it can also be run as a normal Python script.
```console
$ slowdash-activate-venv
$ python slowtask-mytask.py
```

The SlowDash server can perform the following operations on SlowTasks:

- **Start**: Start the SlowTask as a child process. The start command can be specified in `SlowdashPoject.yaml`; by default it runs locally using the `slowdash-task` command.
- **Stop**: If the task has a Heartbeat, call the task's `_sd_stop()` function over SlowMesh.
- **Kill**: If the task was started by the server as a child process, send a KILL signal to the child process.
- **Purge**: For a task whose Heartbeat has disappeared, publish `sd.task.exit` on its behalf to remove it from SlowMesh.


Even a SlowTask process started independently can be stopped from the SlowDash server. However, it cannot be forcibly killed by the server.

By default, a SlowTask process started from inside the SlowDash server automatically exits when the SlowDash process exits.
(It is also forcibly terminated if the server crashes or is forcibly killed.)
A SlowTask process started independently continues running even if the SlowDash server stops, and automatically reconnects when a SlowDash server starts again at the same connection URL.


## SlowTask Identification
Each running SlowTask instance (the running script) has two names: TaskName and MeshID.

- TaskName: A name assigned by the user (or, by default, the filename). It can be predicted before execution. Multiple tasks with the same name are expected to be possible.
- MeshID: A name assigned by the system at runtime. It cannot be predicted until runtime. It is guaranteed that no two tasks in the same mesh have the same MeshID.

RPC calls and similar operations use TaskName because the destination name is known in advance. If multiple tasks have the same TaskName, the RPC call is sent to all of them. RPC replies, on the other hand, use the caller's MeshID so that the reply returns only to the task that made the call.
In many situations, user scripts use TaskName while MeshID is used internally.

By default, running multiple copies of the same script at the same time gives them the same TaskName, but the user can always specify TaskName explicitly. TaskName can be specified in the following ways:

- The task-script filename (default)
- The `name` argument of `Tasklet.run()`
- The `--name` parameter of the `slowdash-task` command
- The `name` parameter in the `task` section of `SlowdashProject.yaml`

TaskName may contain only alphanumeric characters and `_`. Any other characters are replaced with `_`.

To run multiple copies of the same script, multiple entries using the same script but different names can be created in `SlowdashProject.yaml`.

To automatically run many tasks at once, another option is to create a Python script (a Spawn Script) that launches many `slowdash-task` commands with the `--name=NAME` option, and configure `SlowdashProject.yaml` to start only that script.
With this configuration, initial values and distribution of commands by PubSub and RPC can also be finely controlled from within the Spawn Script.
The `slowdash-task` command automatically exits when the parent process that launched it exits, so when the Spawn Script exits, all tasks launched from it also terminate automatically.

## SlowTask Functions
### Lifespan Callbacks
Decorators provided by tasklet can call functions in a SlowTask at specific times or at fixed intervals.
The same decorator can be used multiple times.
In particular, using multiple small `@tasklet.loop(interval)` callbacks makes it possible to avoid explicit loops in the script and reduces the complexity associated with sleeps and shutdown processing.

- `@tasklet.initialize()`: Called when the script starts
- `@tasklet.finalize()`: Called when the script terminates
- `@tasklet.once(delay:float=0)`: Called the specified number of seconds after initialize
- `@tasklet.schedule(time:str, use_utc:bool=False)`: Called repeatedly at specified times
- `@tasklet.loop(interval:float, ticks=None)`: Called repeatedly at the specified interval in seconds

#### Scheduled Execution
The `@tasklet.schedule(time)` decorator repeatedly calls a user function at specified times.

```python
@tasklet.schedule("08:00"):
def do_this_every_morning():
   # Run every morning at 08:00
```

The `time` argument is specified in `HH:MM` format. Wildcard `*` may be used for `HH` and `MM`, and multiple time settings can be listed separated by `,`. To prevent the interval from changing when daylight saving time changes, set `use_utc` to `True` and specify the time in UTC.

Examples:

- `@tasklet.schedule("08:00")`: Every morning at 08:00
- `@tasklet.schedule("00:00,08:00,16:00")`: Three times per day
- `@tasklet.schedule("*:00")`: At minute 00 of every hour
- `@tasklet.schedule("*:*")`: Every minute
- `@tasklet.schedule("*:00,*:20,*:40")`: Three times per hour
- `@tasklet.schedule("08:00", use_utc=True)`: Every day at 08:00 UTC

Unless `use_utc` is specified, the time is local time. Note, however, that when running inside Docker or another container, the local time is often UTC.

#### User Loops
The `@tasklet.loop(interval)` decorator repeatedly calls a user function at the specified interval.

```python
@tasklet.loop(interval=1):
async def my_work():   # This function is called every 1 second (the value of interval)
    #... do my work
```

In addition, if `ticks` is specified for `@tasklet.loop` and a `tick` argument is added to the user function, the value of `tick` becomes True once every number of calls specified by `ticks`.
```python
@tasklet.loop(interval=1, ticks=10):
async def my_work(tick):
    # Read data every second and send all data to the stream
    data = await HV.ch(0).aio_get()
    packet = DataPacket(data, tag='HV.ch00')
    
    await tasklet.mesh.aio_publish('data.stream.HV.ch00', packet)
    
    # Record in the database once every 10 calls
    if tick:
        await tasklet.mesh.aio_publish('data.store.HV.ch00', packet)
```

Multiple tick intervals can also be specified.
```python
@tasklet.loop(interval=1, ticks={"transient_store":10, "store":60}):
async def my_work(tick):
    # Read data every second and send all data to the stream
    data = await HV.ch(0).aio_get()
    packet = DataPacket(data, tag='HV.ch00')
    
    await tasklet.mesh.aio_publish('data.stream.HV.ch00', packet)
    
    # Record in the temporary database (short-term, high-density) once every 10 calls
    if tick.transient_store:
        await tasklet.mesh.aio_publish('data.transient_store.HV.ch00', packet)
        
    # Record in the persistent database once every 60 calls
    if tick.store:
        await tasklet.mesh.aio_publish('data.store.HV.ch00', packet)
```

Again, do not use `time.sleep()` inside user functions. (`await control_system.aio_sleep()` is allowed.)
Using `@tasklet.loop()` should eliminate the need for most sleeps.

### SlowMesh Functions

A SlowTask internally holds a connected SlowMesh instance and can use SlowMesh communication functions through it.

#### Message Exchange with PubSub
At present, values passed in data and headers are limited to JSON-serializable values.
<br>(TODO: support binary data)

- Publish data: `await tasklet.mesh.aio_publish(name:str, packet:XXXPacket)` (async method)
- Subscribe to data: `@tasklet.mesh.on(topic:str)` (decorator; the decorated function receives `packet:XXXPacket`)

#### Accessing the Registry (Key-Value Store)
- Write (set): `await tasklet.mesh.registry.aio_set(key, value, *, cas_revision:int|None=None) -> int|None`
- Read (get): `await tasklet.mesh.registry.aio_get(key:str, default:Any=None, *, with_meta:bool=False) -> Any`
- List keys (keys): `await tasklet.mesh.registry.aio_keys(prefix:str='', limit:int|None=1000)->list[str]`
- Delete (delete): `await tasklet.mesh.registry.aio_delete(key:str, *, cas_revision:int|None=None) -> bool`

#### Exporting Functions and Variables
- Export a function: `@tasklet.mesh.export` (decorator)
- Export a function under a specified name: `@tasklet.mesh.export(name:str)` (decorator)
- Export a SlowPy Control Node: `tasklet.mesh.export(name:str, node:slowpy.control.ControlNode)` (method)

**Exported functions should complete immediately, with a return time of at most about 1 second.**
The caller times out after several seconds.
For long-running processing, consider the following approaches:

- Store the processing request in a variable or place it in an `asyncio.queue`, and have `@tasklet.loop()` observe it and start the processing
- Submit it to `asyncio.create_task()`
- TODO: Add a `threading=True` option to `@export()` to automatically create a background thread

The intended pattern is to publish processing results, and on errors either publish an alert or write to a log.
If necessary, progress can be published incrementally or state can be recorded in the Registry so that the caller can monitor the processing status.
For systems requiring high reliability, one advanced approach is to run a SlowTask that subscribes to `sd.rpc.>` and monitors whether the system transitions to the expected state.

### Dynamic Generation of Config Content
The `@content(name:str)` decorator can dynamically generate the contents of files that would normally be placed under the SlowDash project's `config` directory. In the following example, the browser sees an HTML file named `html-disk_usage.html` as though it existed in `config`, while its contents change each time it is reloaded. By checking `On update: reload HTML` in the browser's HTML form, new HTML can be generated and displayed each time data is updated.

```python
@tasklet.content('config/html-disk_usage.html')
def html_disk_usage():
    total, used, free = tuple((int(x*1e-8)/10.0) for x in shutil.disk_usage('.'))
    return f'''
    <table>
      <tr><td>Total</td><td>{total} GB</td></tr>
      <tr><td>Used</td><td>{used} GB</td></tr>
      <tr><td>Free</td><td>{free} GB</td></tr>
    </table>    
    '''
```

`config/slowplot-XXX.json` can be generated in the same way, so together with an HTML form, a SlowTask can provide a complete layout for using it. A SlowTask itself is an ordinary Python script, so it is also possible to combine a template engine such as Jinja within the script to generate dynamic SlowDash layouts or HTML pages.


### Redirecting Standard Input/Output to SlowMesh PubSub
If the `mesh_stdio` parameter of the Tasklet constructor is set to `True` (the default), standard input/output such as `print()` and `input()` in the user script is redirected to PubSub. TODO: This is connected to the Web Console through the SlowDash server.

- `print()` and `write()` to `stdout`/`stderr`: output to the console and publish to `sd.task.stdout.{task_name}{mesh_id}`
- `input()`: read from console input or from messages on `sd.task.stdin.{mesh_id}`


### Interface to SlowDash Mesh Services
Tasklet also performs other internal processing required for SlowMesh connections.

- Sending Heartbeats
- Responding to specification queries (`sd.task.introduce`)
- Exporting the `_sd_stop()` function for termination requests
- Notification to `sd.task.exit` on termination


## When Tasklet Is Not Explicitly Used in a Script
Even when Tasklet is not explicitly used in a script, an arbitrary Python script can still be used as a SlowTask. In this case, only the following functions are available.

- start/stop/kill control from the SlowDash server
- Export of all functions (for calls from other tasks or browsers)
- Old-style callbacks:
  - `_initialize(params={})`: equivalent to `@tasklet.initailze()`
  - `_finalize()`: equivalent to `@tasklet.finalize()`
  - `_run()`: equivalent to `@tasklet.once()`
  - `_loop()`: equivalent to `@tasklet.loop(interval=0)`
  - `_get_html()`: equivalent to `@tasklet.content('config/html-{name}.html')`
  - `_get_layout()`: equivalent to `@tasklet.content('config/slowplot-{name}.json')`


# Example Projects
Examples using the basic SlowTask functions are available in `ExampleProjects/Experimental/Mesh/`.

- `slowtask-randomwalk.py` generates dummy data and publishes it to `data.store.HV.ch0.V`
- `slowtask-store.py` subscribes to `data.store.>` and stores the received data in a SlowPy DataStore
- `slowtask-histogram.py` subscribes to `data.*.>`, creates histograms from the received data, and publishes them to `data.stream.histogram.{Channel}`
- Set-point configuration for `slowtask-randomwalk.py` from the browser via RPC
- start/stop control for `slowtask-randomwalk.py` from the browser via PubSub
- `slowtask-store.py` exports the `disk_usage` variable, which the browser displays as data

### Running
#### Automatically Start and Stop Tasks Together with the Server
In `SlowdashProject.yaml`, these SlowTasks are configured to start automatically with the server and stop automatically when it terminates.
Even if a task runs out of control, the server can forcibly terminate it with a signal.
Even if the server crashes or is immediately force-killed externally (SIGKILL), the tasks automatically terminate at the same time.

```yaml
slowdash_project:
  name: SlowMesh_Test
  
  data_source:
    - url: sqlite:///TestData
      time_series:
        schema: slowdata [channel] @timestamp(unix) = value

  tasks:
    - name: randomwalk
      auto_start: true

    - name: histogram
      auto_start: true
      
    - name: store
      auto_start: true
```

```console
$ slowdash --port=18881
```

#### Start Tasks Manually and Stop Them Together with the Server
If `auto_start` is set to `false` or commented out, these tasks are not started automatically.
In that case, they can be started by clicking Start in the SlowDash task control panel.
Tasks started from the control panel automatically terminate when the server terminates.
If a task runs out of control, the server can also forcibly terminate it using a signal.

#### Run Tasks Independently of the Server
Tasks for which automatic start is not configured, or for which no task entry is present at all, can run independently of the server.
In this case, open a new terminal and use the `slowdash-task` command to run the SlowTask.
As long as the task can access SlowMesh, the task process may run on another PC or in another container.
It should be possible to stop and restart a task process while leaving the SlowDash server process running.
Likewise, if the task process remains running while the SlowDash server is stopped and restarted, it should reconnect automatically.
```console
$ cd PATH/TO/PROJECT
$ slowdash-task config/slowtask-store.py --mesh=slowmq://localhost:18881
```
Even in this case, a "termination request" can be issued to the task from the SlowDash task control panel.
If the task is implemented with Tasklet and is not hung, this should normally terminate it cleanly.
A task started independently of the server cannot be forcibly terminated by a signal from the server.


### Components

#### Readout Task (`slowtask-randomwalk.py`)
The RandomWalk task reads dummy data once per second in a tasklet loop callback and publishes it to the `data.store.HV.ch0.V` topic.
```python
@tasklet.loop(interval=1.0)
def loop():
    if not device.is_running:
        return
    data = device.ch(0).get()
    tasklet.mesh.publish('data.store', DataPacket(data, tag='HV.ch0.V'))
```

Readout start and stop are controlled by the PubSub topics `control.start` and `control.stop`.
The operating state is also recorded in the Registry when starting and stopping.
```python
@tasklet.mesh.on('control.start')
async def start(params):
    device.is_running = True
    await tasklet.mesh.registry.aio_set('setup.run.status', 'running')

@tasklet.mesh.on('control.stop')
async def stop(params):
    device.is_running = False
    await tasklet.mesh.registry.aio_set('setup.run.status', 'idle')
```

The set point of the RandomWalk virtual device is configured through an exported RPC (for demonstration purposes). In actual use, PubSub could be used in the same way as Start/Stop.
```python
@tasklet.mesh.export
def set_value(value:float):
    device.ch(0).set(value)
```

#### Data Storage Task (`slowtask-store.py`)
Data published by the RandomWalk task is subscribed to by the store task and recorded in the database.
```python
@tasklet.mesh.on('data.store.>')
def store(data:DataPacket):
    datastore.append(data.values, tag=data.tag, timestamp=data.timestamp)
```

Even if multiple processes publish data, all data is written to the database in this one place, so write conflicts can be avoided even when using a database such as SQLite that does not provide transactions for this use case.
The description of the data format (table schema) can also be centralized in one place.

##### Addition 1
The Store task in this example exports a ControlNode instance named `disk_usage` that returns disk capacity information, and returns it in response to an external "data request."
```python
import shutil
from slowpy.control import ControlNode

class DiskUsageNode(ControlNode):
    async def aio_get(self):
        total, used, free = tuple((int(x*1e-8)/10.0) for x in shutil.disk_usage('.'))
        return {
            'tree': {
                'total_GB': total,
                'used_GB': used,
                'free_GB': free,
                'used_percent': int(100 * used/total) if total > 0 else 100
            }
        }

tasklet.mesh.export('disk_usage', DiskUsageNode())
```

Through the SlowTask HTTP API, variables exported by a task can be accessed in the same way as data stored in the database. (They appear as though a single data point with a timestamp of "now" were stored.)

Whereas publish is fundamentally a push from the data source, exporting a ControlNode provides a pull interface that returns data in response to an external request. It is suitable for cases where the latest value is needed on demand.

##### Addition 2
The Store task in this example also includes an example of dynamically generating files that would normally be placed under the SlowDash project's `config` directory.
`@content(name)` associates a content name with the function that generates it.

```python
@tasklet.content('config/html-disk_usage.html')
def html_disk_usage():
    total, used, free = tuple((int(x*1e-8)/10.0) for x in shutil.disk_usage('.'))
    used_percent = int(100 * used/total) if total > 0 else 100
    return f'''
        <span style="font-size:300%">{used_percent}</span>
        <span style="font-size:250%">% used</span>
        <p>
        <table>
          <tr><td>Total</td><td>{total} GB</td></tr>
          <tr><td>Used</td><td>{used} GB</td></tr>
          <tr><td>Free</td><td>{free} GB</td></tr>
        </table>    
    '''
```

If "On update: reload HTML" is checked in the browser's HTML form, this content-generation function is called each time the data is updated, allowing an HTML page containing data to be generated dynamically.

#### Data Analysis Task (`slowtask-histogram.py`)
Data published by the RandomWalk task is subscribed to and analyzed by the Histogram task.
The resulting histograms are published to `data.stream.histogram.{Channel}`.

```python
@tasklet.mesh.on('data.*.HV.>')
def process_data(headers, body):
    if not is_running:
        return
    
    for channel, data in body.items():
        if channel not in histograms:
            print(f'creating a histogram for channel {channel}')
            histograms[channel] = Histogram(100, -50, 50)
        histograms[channel].fill(data.get('x', []))


@tasklet.loop(interval=1)
def stream_hist():
    if not is_running:
        return
    
    for channel, hist in histograms.items():
        tasklet.mesh.publish('data.stream', DataPacket(hist, tag=f'histogram.{channel}'))
```
Arrival-data analysis and histogram publishing are separate callbacks so that histograms are published at a fixed interval regardless of the incoming data rate.
Because the data-storage task subscribes only to `data.store.>`, data published to `data.stream` is not stored and appears only on the online display.

In addition to subscribing to start/stop, the `is_running` status is read during initialize from the value set by RandomWalk in the Registry, so the status is handled correctly even if the analysis process is stopped and restarted.
```python
@tasklet.initialize()
async def initialize():
    global is_running
    is_running = (await tasklet.mesh.registry.aio_get('setup.run.status', 'dead') == 'running')

@tasklet.mesh.on('control.start')
async def start():
    global is_running
    is_running = True

@tasklet.mesh.on('control.stop')
async def stop():
    global is_running
    is_running = False
```


#### Web Form (`html-startstop.html`)
The browser Web form publishes start/stop commands and performs set-point RPC calls.
```html
<form name="run_control">
  <b>Device Controls</b> (Function Call)<br>
  V0 Set Point: <input type="number" name="V0_setpoint" value="10">
  <button name="randomwalk.set_value()">Set</button>
  <p>  
  <b>Run Controls (V0)</b> (Publish)<br>
  <button name="publish control.start()">Start</button>
  <button name="publish control.stop()">Stop</button>
  <p>  
  <b>Run Controls (V1)</b> (No-Tasklet Function Call)<br>
  <button name="no_tasklet.start()">Start</button>
  <button name="no_tasklet.stop()">Stop</button>
</form>
```
The `name` attribute of a button (`<button>` or `<input type="submit">`) describes the action to perform when the button is clicked.

- `randomwalk.set_value()`: Remotely call the `set_value()` function of the randomwalk task. The function arguments are formed by combining the argument list written here (empty in this example) with the name-value pairs of the other `<input>` elements.
- `publish control.start()`: Publish to the `control.start` topic. The published data is a JSON object combining the argument list (empty in this example) with the name-value pairs of the other `<input>` elements.

In addition, when a `name` is specified on the `<form>` element, a change in an `<input>` field causes the changed value to be published to the `form.input.{form_name}` topic. At the same time, the page subscribes to this topic so that when the same form is changed in another browser, the change is immediately reflected.

#### SlowPlot Layout (`slowplot-control.json`)
This layout arranges the following elements:

- Web form for controlling the readout task (`html-startstop.html`)
- Plot of data stored in the database by the Store task (time-series plot of `HV.ch0.V`)
- Display of online analysis results streamed by the Histogram task (`data.stream.histogram.HV.ch0.V` plot)
- Display of values received directly from data published by the RandomWalk task through the streaming channel (Single Value Display of `HV.ch0.V`)
- Display of `disk_usage` exported by the Store task (`store.data_usage` data channel)
- Display of HTML content dynamically generated by the Store task (disk-usage table; dynamically generated `config/html-disk_usage.html` file content)
- Display of values held in the Registry
  - Display the value of `randomwalk.run.status` as a Single Scalar (`@registry:randomwalk.run.status` data channel)
  - Display the entire subtree below `randomwalk` as a Tree (`@registry:randomwalk` data channel)
  - Display the entire PubSub Last-Value Cache as a Tree (`@registry:pubsub.>` data channel)


# HTTP API
## SlowTask

The HTTP API for SlowTask is implemented by the `sd_task.py` component through Slowlette.

### Task Control
#### GET `api/task/catalog`
Returns a list of task settings derived from task configuration, script files, and related information.

```json
{
  "randomwalk": {
    "name": "randomwalk",
    "file_path": "config/slowtask-randomwalk.py",
    "command": "slowdash-task config/slowtask-randomwalk.py --name=randomwalk",
    "auto_start": true
  },
  "store": {
    "name": "store",
    "file_path": "config/slowtask-store.py",
    "command": "slowdash-task config/slowtask-store.py --name=store",
    "auto_start": true
  },
}
```

#### GET `api/task/status`
Returns a list of the status of all running tasks, including Task Specs.

```json
[
  {
    "name": "store",
    "proc_id": [ 17769 ],
    "heartbeat_expire": 1787536123,
    "spec": {
      "mesh_id": "store_vp13_17769_1",
      "name": "store",
      "timestamp": 1787535529.8033955,
      "heartbeat_interval": 5,
      "functions": {},
      "variables": { ... },
      "contents": { ... },
      "stdio": {
        "stdin": [ "sd.task.stdin.store.store_vp13_17769_1" ],
        "stdout": [ "sd.task.stdout.store.store_vp13_17769_1" ],
        "stderr": [ "sd.task.stdout.store.store_vp13_17769_1" ]
      }
    }
  },
  {
    "name": "randomwalk",
    ...
```


#### POST `api/task/control/{taskname}`
Starts, stops, or forcibly terminates the specified task.

- The Body contains only the `action` field. The value of `action` is one of `start` / `stop` / `kill`.
  - `start` is available only when the catalog contains a `command`. The task is executed as a child process using `Popen()`.
  - `stop` is available only when a Heartbeat exists on SlowMesh. The Tasklet `_sd_stop()` function is called through SlowMesh RPC.
  - `kill` is available only when status contains a `pid` (a SlowTask started externally cannot be killed). SIGKILL is sent.
    - Even if the `command` is `ssh`, when RetainerAutocide is configured (the default for `slowdash-task`), a SlowTask running as a child process of ssh should also be killed.

### General Control Interface
#### POST `api/control`
Mesh request.

- The Body is a JSON document containing HTML Form input values (an object collecting the `name` and `value` of `<input>` elements in the form).
- The `name` of a `<button>` element (or an `<input type="submit">` element) is interpreted as the request.

##### RPC Call Request (compatible with the old slowtask function-call format)
- Syntax: `task_name.function_name(fixed_parameter_list)`
- Example: `<button name="run_controller.start(run_mode='normal')">`
- The RPC arguments are formed by adding the fixed parameters to the `name` and `value` pairs of the `<input>` elements in the Form (excluding elements with `type="submit"`).
- The RPC signature is inspected so that only required parameters are selected, with type checking and type conversion also performed.
- Response:
  - Success: 200, `{ "status": "ok", "return_value": return_value }`
  - RPC error (exception at the called destination): 200, `{ "status": "error", "message": error_message }`
  - RPC cancellation (Async-Task Cancelled at the called destination): 200, `{ "status": "cancelled" }`
  - Other errors: a 4xx error response

##### Publish Request
- Syntax: `publish topic_name(fixed_parameter_list)`
- Example: `<button name="publish my_setup.start(run_mode='normal')">`
- A JSON object of Key-Value Pairs is published, formed by adding the fixed parameters to the `name` and `value` pairs of the `<input>` elements in the Form (excluding elements with `type="submit"`).
- Response:
  - Success: 200, `{ "status": "ok" }`
  - Error: a 4xx error response


### General Data Interface

#### GET `api/channels`
Returns the names of variables exported by Tasks, listed in the same format as data in the database.

#### GET `api/data/{channels}?length={length}&to={to}`
Returns values of variables exported by Tasks in the same format as data in the database.

- Values are returned only if the query period specified by `length` and `to` includes the current time (typically a query with `to` equal to `0`).


### General Config Interface

#### GET `api/config/contentlist`
For contents provided by Tasks whose names begin with `config/`, generates and returns a list in the same form as files under the SlowDash Project `config` directory.

#### GET `api/config/content/{content_name}`
Returns the contents of Task-provided content whose name begins with `config/`.


## Registry (Key-Value Store)

The HTTP API for Registry is implemented by the `sd_mesh_registry.py` component through Slowlette.

### Registry Access

#### GET `api/registry/value/{key}`
Returns the value held in the Registry (`with_meta=true` returns a JSON document including metadata).

#### GET `api/registry/keys?prefix={prefix}&limit={limit}`
Returns a list of keys held in the Registry.

### General Data Interface

#### GET `api/data/{channels}?length={length}&to={to}`
Returns values of keys held in the Registry as data (in the same format as data from the database).

- Applies to channels of the form `@registry:{key}`
- TODO: Apply when the Registry metadata interval [updated, now()] overlaps the data query period


## WebMesh
WebMesh is a bridge that makes SlowMesh PubSub available over HTTP. It is implemented by the `sd_webmesh.py` component through Slowlette.

### PubSub

#### EventSource(`event/webmesh/attach`)
Creates an SSE connection channel.

  - `register` event: the server distributes a ClientID
  - `data` event: messages on the `data.*.>` topic
  - `stdout` event: messages on the `sd.task.stdout.>` topic

#### POST `api/webmesh/subscribe/data?client_id={client_id}`
Specifies a channel to Subscribe to for data streaming. It may be called multiple times.
Specify `channel` as JSON in the POST body.

#### POST `api/webmesh/unsubscribe`
Cancels all subscriptions.

#### POST `api/webmesh/publish/{topic}`
Publishes to SlowMesh.

### General Data Interface

#### GET `api/channels`
Returns a list of data channels flowing on `data.*` topics.



# RPC Services
## User-Defined Namespace
#### Export Module Name (SlowMesh Task Name)
- All names except those beginning with `sd_` are in the user namespace

#### Export Function Name (exported function within a module)
- All names except those beginning with `_` are in the user namespace
  - Names beginning with `_sd_` are used by SlowMesh core functions
  - `_setup()`, `_initialize()`, `_finalize()`, `_loop()`, and `_run()` are reserved callbacks for No-Tasklet Tasks (backward compatibility)


## Registry (Key-Value Store)
- Module name: `sd_mesh_registry`
- Exported functions:
  - Write: `async def aio_set(self, key, value, *, cas_revision:int|None=None) -> int|None`
  - Read: `async def aio_get(self, key:str, default:Any=None, *, with_meta:bool=False) -> Any`
  - List keys: `async def aio_keys(self, prefix:str='', limit:int|None=1000)->list[str]`
  - Delete: `async def aio_delete(self, key:str, *, cas_revision:int|None=None) -> bool`


## Task RPC
- Module name: `{task_name}` (by default, the script filename is `slowtask-{task_name}.py`)
- Exported functions:
  - Functions decorated with `@export` in the Task Script
  - `_sd_stop()`: stop request
  - `_sd_get_content(name:str)`: obtain Task Contents


# Registry Services
## User-Defined Namespace
- All names beginning with an uppercase letter (such as `P8.>` or `KamLAND.>`)
- `setup.>`
- `user.>`
- `my.>`
- `test.>`

## SlowDash Server Information
- `server.url`

## PubSub Last-Value Cache
- `pubsub.{topic}`


# PubSub Topic Structure
## User-Defined Namespace
- All names beginning with an uppercase letter (such as `P8.>` or `KamLAND.>`)
- `setup.>`
- `user.>`
- `my.>`
- `test.>`


## data
### data.store.{channel_name} / data.stream.{channel_name}
##### Topic Name Structure
- `data.store.{channel_name}`: persistent data
- `data.stream.{channel_name}`: monitoring data

##### MeshPacket
`DataPacket(values, *, tag:str|None=None, timestamp:float|None=None)`

- Same arguments as `DataStore.append()`

##### Format
SlowDash standard data format


## form
### form.inputs.{form_name}

##### Primary Uses
- Purposes
  - Notify all browsers of changes to browser-form input values
  - Save browser-form input values in the Registry so that they can be used as initial values when a new page is opened
  - Reflect browser-form operations immediately in control
- Sender(s): sd_task (SlowDash server)
- Receiver(s): sd_task (SlowDash server), Registry, task process
- Timing:
  - `change` event of an INPUT field in a browser form
  
##### JSON Schema
Body:
```json
{
    "type": "object",
    "required": [ "sender_id", "form", "values" ],
    "properties": {
        "sender_id": { "type": "string" },
        "form": { "type": "string" },
        "values": { "type": "object" }
    }
}
```

##### JSON Example
Body:
```json
{
    "sender_id": "eab2b828-006b-4d87-a01e-4d308ca71226",
    "form": "run_control",
    "values": {
        "V0_setpoint": 100,
        "V1_setpoint": 80
    }
}
```


## sd.task
- Every SlowTask Process must subscribe to `sd.task.control.>`.

### sd.task.heartbeat.{task_name}.{mesh_id}
Task liveness signal. The Body records expire (= time-of-heartbeat + heartbeat-interval). If Expire is earlier than the current time, the Heartbeat is considered absent.

##### Primary Uses
- Sender(s): task process
- Receiver(s): sd_task (SlowDash server), monitoring service
- Timing:
  - At the specified interval (`Tasklet._heartbeat_interval`, 10 seconds)
  - Sent from Tasklet's main loop (not from a coroutine or thread; it always stops together with the main loop. It also stops if the user calls `time.sleep()`.)

##### Secondary Use
- If the server receives a Heartbeat from a task it does not know, it publishes `sd.task.control.introduce` on PubSub

##### Third Use
- Reconnection after a PubSub connection loss caused by a server crash or similar event is triggered by publish, so sending Heartbeats serves as reconnect retries after disconnection
- Reconnection also triggers actions such as retransmission of `sd.task.spec`
- Resumption of the system after server recovery is therefore delayed by approximately one heartbeat interval

##### JSON Schema
Headers:
```json
{
    "type": "object",
    "required": [ "mesh_id", "name", "timestamp" ],
    "properties": {
        "mesh_id": { "type": "string" },
        "name": { "type": "string" },
        "timestamp": { "type": "int" }
    }
}
```

Body:
```json
{
    "type": "object",
    "required": [ "expire" ],
    "properties": {
        "expire": { "type": "int" }
    }
}
```

##### JSON Example
Headers:
```json
{
    "mesh_id": self.mesh_id,
    "name": self.name,
    "timestamp": int(time.time())
}
```

Body:
```json
{
    "expire": int(time.time()) + self.interval
}
```

### sd.task.spec.{task_name}.{mesh_id}
List of functions and variables exposed externally by the task.

##### Primary Uses
- Sender(s): task process
- Receiver(s): sd_task (SlowDash server)
- Timing:
  - When the task starts
  - When `sd.task.control.introduce` is received

##### JSON Schema
Body:
```json
{
    "type": "object",
    "required": [ "mesh_id", "name", "timestamp", "functions", "variables" ],
    "properties": {
        "mesh_id": { "type": "string" },
        "name": { "type": "string" },
        "timestamp": { "type": "int" },
        "functions": {
            "type": "object",
            "required": [],
            "properties": {
                "kwargs": {
                    "type": "object",
                    "properties": {
                        "type": { "type": "string", "enum": [ "int", "float", "str", "bool" ] },
                        "default": { }
                    }
                },
                "arbitrary_keywords": { "type": "bool" }
            },
        },
        "variables": {
            "type": "object",
            "required": [ "type" ],
            "properties": {
                "type": { "type": "string", "enum": [ "control_node" ], "$comment": "Other types such as dataclass may be added in the future. Perhaps readonly as well." },
                "data_type": { "type": "string", "enum": [ "numeric", "string", "tree", "table", "histogram", "graph" ] },
                "probe_value": {}
        },
        "stdio": {
            "type": "object",
            "properties": {
                "stdout": { "type": "string", "$comment": "Topic name to which stdout is published" }, 
                "stderr": { "type": "string", "$comment": "Topic name to which stderr is published" }, 
                "stdin": { "type": "string", "$comment": "Topic name whose subscribed messages are sent to stdin" }
            }
        }
    }
}
```

##### JSON Example
Body:
```json
{
    "name": "mytask",
    "functions": {
        "start": {
            "kwargs": { "run_number": { "type": "int", "default": -1 } },
            "arbitrary_keywords": false
        },
        "stop": {
            "arbitrary_keywords": false
        }
    },
    "variables": { "status": { "type": "node" } }
}
```

### sd.task.exit.{task_name}.{mesh_id}
Notifies that the task has terminated.

##### Primary Uses
- Sender: task process
- Receiver(s): sd_task (SlowDash server), monitoring service
- Timing:
  - When the Task terminates

##### JSON Schema
Body:
```json
{
    "type": "object",
    "required": [ "mesh_id", "name", "timestamp", "had_error" ],
    "properties": {
        "mesh_id": { "type": "string" },
        "name": { "type": "string" },
        "timestamp": { "type": "int" },
        "had_error": { "type": "bool" }
    }
}
```


### sd.task.control.introduce
Requests all tasks to publish `sd.task.spec.{task_name}.{mesh_id}`.

##### Primary Uses
- Sender: sd_task (SlowDash server)
- Receiver(s): task process
- Timing:
  - When the SlowDash server starts
  - When the SlowDash server receives a heartbeat from a task it does not know

##### JSON Schema
Body:
```json
{
    "type": "object",
    "required": [],
    "properties": {}
}
```

### sd.task.life_event.{task_name}.{mesh_id}
Notifies changes in the task's execution state as observed externally.

##### Primary Uses
- Sender(s): sd_task (SlowDash server) / slowdash-task (script loader)
- Receiver(s): task monitors through sd_webmesh, etc.
- Timing:
  - When the SlowTask loader loads a script (`script loaded`)
  - When the SlowTask loader fails to load a script (`script loading failed`)
  - When the server receives a task spec (`registered`)
  - When the server receives task exit (`completed` / `died in error`)
  - When the server monitor detects that a heartbeat has stopped (`heartbeat stopped`)
  - When the server monitor detects that a heartbeat has recovered (`heartbeat recovered`)

##### JSON Schema
Body:
```json
{
    "type": "object",
    "required": [ "mesh_id", "timestamp", "event" ],
    "properties": {
        "mesh_id": { "type": "string" },
        "name": { "type": "string" },
        "timestamp": { "type": "int" },
        "event": { "type": "string" },
    }
}
```


### sd.task.stdout.{task_name}.{mesh_id}
Redirects output written to the task's stdout/stderr.

##### Primary Uses
- Sender: task process
- Receiver(s): task monitors and Web Console through sd_webmesh, etc.

##### JSON Schema
Headers:
```json
{
    "type": "object",
    "required": [ "name", "mesh_id", "stream" ],
    "properties": {
        "mesh_id": { "type": "string" },
        "name": { "type": "string" },
        "stream": { "type": "string", "enum": [ "stdout", "stderr" ] }
    }
}
```

Body:
```json
{
    "type": "object",
    "required": [ "name", "mesh_id", "timestamp", "stream", "kind", "text" ],
    "properties": {
        "mesh_id": { "type": "string" },
        "name": { "type": "string" },
        "timestamp": { "type": "int" },
        "stream": { "type": "string", "enum": [ "stdout", "stderr" ] },
        "kind": { "type": "string", "enum": [ "text" ] },
        "text": { "type": "string" }
    }
}
```

### sd.task.stdin.{mesh_id}
Injects input into the task's `input()` through PubSub.

##### Primary Uses
- Sender(s): task monitors and Web Console through sd_webmesh, etc.
- Receiver: task process

##### JSON Schema
Body:
```json
{
    "type": "object",
    "properties": {
        "text": { "type": "string" }
    }
}
```


## sd.rpc
Used internally by Mesh to implement RPC.

### sd.rpc.{module_name}
##### JSON Schema
Header:
```json
{
    "type": "object",
    "required": [ "sender", "sender_id", "reply_to", "correlation_id", "message_id", "module", "function" ],
    "properties": {
        "sender": { "type": "string" },
        "sender_id": { "type": "string" },
        "reply_to": { "type": "string" },
        "correlation_id": { "type": "string" },
        "message_id": { "type": "string" },
        "module": { "type": "string" },
        "function": { "type": "string" }
    }
}
```
Body:
```json
{
    "type": "object",
    "properties": {
        "args": { "type": "array" },
        "kwargs": { "type": "object" }
    }
}
```

##### JSON Example
Header:
```json
{
    "sender": self._name,
    "sender_id": self._mesh_id,
    "reply_to": f"sd.rpc_reply.{self._mesh_id}",
    "correlation_id": self._request_count,
    "message_id": str(uuid.uuid4()),
    "module": module_name,
    "function": function_name,
}
```
Body:
```json
{
    "args": args,
    "kwargs": kwargs
}
```

### sd.rpc_reply.{mesh_id}
The topic name `sd.rpc_reply.{mesh_id}` is specified by `reply_to` in `sd.rpc`.
The `mesh_id` here is the MeshID of the side that sent the RPC request.


##### JSON Schema
Header: Same contents as the request message except for `sender`, `sender_id`, and `message_id`.
```json
{
    "type": "object",
    "required": [ "sender", "sender_id", "correlation_id", "message_id", "module", "function" ],
    "properties": {
        "sender": { "type": "string" },
        "sender_id": { "type": "string" },
        "correlation_id": { "type": "string" },
        "message_id": { "type": "string" },
        "module": { "type": "string" },
        "function": { "type": "string" }
    }
}
```
Body:
```json
{
    "type": "object",
    "required": [ "status", "message", "return_value" ],
    "properties": {
        "status": { "type": "string", "enum": [ "ok", "error", "cancelled" ] },
        "message": { "type": "string" },
        "return_value": {}
    }
}
```


##### JSON Example
```json
{
    "sender": self._name,
    "sender_id": self._mesh_id,
    "correlation_id": correlation_id,
    "message_id": str(uuid.uuid4()),
    "module": module_name,
    "function": function_name,
}
```
Body:
```json
{
    "status": "ok",
    "message": "ok",
    "return_value": result
}
```




# TODO
- Tasklet Initialize params
- Make it possible to run the Registry as a SlowTask as well
- MyMesh: used when running a SlowTask without SlowMesh. Connect from the console and capture lines beginning with `!!!`
- Task RPC Proxy
- Export of dataclass
