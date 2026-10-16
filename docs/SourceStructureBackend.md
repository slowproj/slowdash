---
title: Source Structure - Python Backend
---

# High-Level Structure

SlowDash is organized in four main Python layers:

```text
Client / CLI / CGI
    |
    v
Slowlette
    - ASGI/WSGI adapter
    - URL routing
    - request argument binding
    - response merging
    |
    v
SlowDash server components
    - project/config handling
    - data source API
    - user module API and Mesh task proxies
    - export API
    - user HTML/content API
    - SlowMQ, WebMesh (SSE), and Mesh registry
    |
    v
Plugins and libraries
    - app/plugin data sources and exporters
    - slowpy data objects, control nodes, stores, client helpers
    - slowpy.mesh pub/sub, RPC, and Tasklet runtime
```

The central server object is `App` in `app/server/slowdash.py`. It subclasses `slowlette.App`, creates a `Project`, adjusts the runtime environment, then includes a list of SlowDash components into the Slowlette router.

Tasks run in separate processes, such as those launched by `slowdash-task`, and communicate with the server through `slowpy.mesh`. The in-process user-module mechanism provided by `UserModuleComponent` remains available.

# Important Directories

### `app/server`

This directory contains the SlowDash web application and built-in API components.

Key files:

- `slowdash.py`: application entry point, command-line entry point, component assembly, internal API helpers.
- `slowdash_wsgi.py` and `slowdash.cgi`: WSGI/CGI entry points.
- `sd_project.py`: project discovery, YAML loading, environment/command substitution, public project metadata.
- `sd_component.py`: base classes for components and plugin-backed components.
- `sd_config.py`: `/api/config`, config file/content APIs, transient content support.
- `sd_datasource.py`: data source plugin base class and `/api/channels`, `/api/data`, `/api/blob` routes.
- `sd_datasource_SQL.py`, `sd_datasource_TableStore.py`, `sd_dataschema.py`: common data-source helpers.
- `sd_blobstorage.py`: blob storage helpers.
- `sd_export.py`: export plugin component.
- `sd_usermodule.py`: in-process user module extension system.
- `sd_task.py`: task catalog, process control, Mesh task discovery, and proxies for RPC, variables, and content.
- `slowdash-task.py`: CLI that loads a task script and runs its `Tasklet` in a separate process.
- `sd_userhtml.py`: user-provided HTML/content serving.
- `sd_console.py`: legacy console capture implementation (not included by the current `App`).
- `sd_misc_api.py`: miscellaneous built-in API endpoints.
- `sd_webmesh.py`: bridge between Mesh topics and browser SSE connections, plus streamed-data caching.
- `sd_mesh_registry.py`: shared Mesh registry, latest pub/sub values, and log collection.
- `sd_slowmq.py`: built-in websocket-based pub/sub component.
- `sd_version.py`: version string.

### `app/plugin`

This directory contains plugin modules loaded by `PluginComponent`.

Data source plugins include:

- `datasource_CSV.py`
- `datasource_SQLite.py`
- `datasource_PostgreSQL.py`, `datasource_PostgreSQL_NoAsync.py`
- `datasource_MySQL.py`, `datasource_MySQL_mysqlclient.py`, `datasource_MySQL_NoAsync.py`
- `datasource_InfluxDB2.py`
- `datasource_Redis.py`, `datasource_Redis_NoAsync.py`
- `datasource_MongoDB.py`
- `datasource_CouchDB.py`
- `datasource_Honeybee.py`
- `datasource_Dummy.py`
- `datasource_SystemResource.py`
- `datasource_YAML.py`

Export plugins include:

- `export_CSV.py`
- `export_Notebook.py`
- `export_Jupyter.py`

Plugin file names and class names are convention-based. For example, a data source of type `SQLite` maps to:

```text
app/plugin/datasource_SQLite.py
DataSource_SQLite
```

### `lib/slowlette`

Slowlette is the small web framework used by SlowDash.

Important files:

- `app.py`: `App` and `Slowlette` application classes.
- `router.py`: decorators, path matching, argument binding, sub-app dispatch, response merging.
- `server.py`: ASGI/WSGI dispatch and development server helpers.
- `request.py`: parsed HTTP request object.
- `response.py`: response object, content merging, file responses.
- `model.py`: JSON request-body wrappers.
- `websocket.py`: websocket wrapper and connection-close handling.
- `eventstream.py`: Server-Sent Events (SSE) wrapper and disconnect handling used by WebMesh.
- `middleware.py`: middleware support.

### `lib/slowpy`

SlowPy provides data types, control abstractions, storage writers, client helpers, plotting helpers, Mesh communication, and task execution.

Important areas:

- Top-level data objects:
  - `basetypes.py`
  - `histograms.py`
  - `graphs.py`
  - `trend.py`
  - `treetable.py`
  - `mpldata.py`
  - `slowplot.py`
- Control system:
  - `control/node.py`
  - `control/system.py`
  - `control/control_*.py`
- Data stores:
  - `store/store.py`
  - `store/factory.py`
  - `store/store_SQL.py`
  - `store/store_CSV.py`
  - `store/store_HDF5.py`
  - `store/store_InfluxDB2.py`
  - `store/store_Redis.py`
- Client helpers:
  - `slowfetch.py`

The public top-level `slowpy` package exports common data objects such as `Histogram`, `Graph`, `Trend`, `Tree`, `Table`, `TimeSeries`, `SlowFetch`, `slowdashify`, and `slowplot`.

### `lib/slowpy/slowpy/mesh`

This communication and execution library is used by both the server and independent tasks.

- `__init__.py`: exports `Mesh`, `Tasklet`, `RetainerAutocide`, `MeshStdio`, `MeshLogHandler`, `DataPacket`, and `FormPacket`.
- `mesh.py`: pub/sub transport selection, topic conversion, RPC, function/control-node exports, remote nodes, and the registry client.
- `tasklet.py`: callback execution, task specifications, heartbeats, shutdown, and parent-process death handling.
- `packet.py`: conversion of data and form updates into topics, headers, and bodies.
- `stdio.py`: thread-aware routing and queues connecting standard input/output to Mesh.
- `logger.py`: handler that publishes Python log records to Mesh.
- `dash.py`: asynchronous HTTP client used by `Tasklet.dash` to fetch configuration, channels, and data.

# Application Startup Flow

## Command-line or server startup

The main entry point is `app/server/slowdash.py`.

The normal startup sequence is:

1. Parse command-line options.
2. Create `App(project_dir=..., project_file=..., port=..., is_cgi=..., is_command=..., is_async=...)`.
3. `App` creates a `Project`.
4. `Project` finds the SlowDash system directory and project directory.
5. `Project` loads `SlowdashProject.yaml`, or creates an initial config from environment variables when configured that way.
6. `App` changes the process working directory to the project directory when available.
7. `App` adds the system plugin directory, project directory, and project `config` directory to `sys.path`.
8. `App` includes all built-in components into its Slowlette router.
9. The app is run as ASGI, WSGI, CGI, or command-line internal request depending on the selected mode.

## Component include order

`slowdash.py` includes components in this order:

```text
SlowMQComponent
MeshRegistryComponent
UserModuleComponent
WebMeshComponent
DataSourceComponent
UserHtmlComponent
ExportComponent
ConfigComponent
MiscApiComponent
TaskComponent
```

This order matters because Slowlette merges matching responses from bottom to top.

- `WebMeshComponent` precedes `DataSourceComponent` so it can fill channels missing from other responses using its cache.
- `UserModuleComponent` is before data sources, but `TaskComponent` is last; the old ordering assumptions for in-process tasks no longer apply.
- `ConsoleComponent` is not included. Task standard I/O and logging use `MeshStdio` and `MeshLogHandler`.

`MeshRegistryComponent`, `WebMeshComponent`, and `TaskComponent` connect to Mesh during `post_startup`. In ASGI, this event runs after `lifespan.startup.complete` has been sent, allowing connections to the built-in SlowMQ WebSocket service. Mesh-based operation requires a valid `project.mesh_url` and a running transport. WebMesh startup is gated by `app.is_async`.

# Slowlette Routing and Response Model

## Request flow

For ASGI:

```text
ASGI server
    |
    v
slowlette.server.dispatch_asgi()
    |
    +-- lifespan.startup/shutdown -> router.dispatch_event()
    |
    +-- websocket -> router.websocket()
    |
    +-- http -> read body -> Request -> router.dispatch()
                (eventstream routes send SSE through EventStream)
```

For WSGI:

```text
WSGI server
    |
    v
slowlette.server.dispatch_wsgi()
    |
    v
Request -> asyncio.run(router.dispatch()) -> WSGI response
```

Slowlette converts the incoming URL into a `Request`:

- `Request.path`: decoded path components.
- `Request.query`: decoded query dictionary.
- `Request.headers`: normalized header dictionary supplied by the server layer.
- `Request.body`: raw body or Python object for internal dispatch.

## Decorators and argument binding

Handlers are declared with decorators such as:

```python
@slowlette.get('/api/channels')
@slowlette.post('/api/control')
@slowlette.websocket('/ws/slowmq')
@slowlette.eventstream('/event/webmesh/attach')
@slowlette.on_event('startup')
```

`PathRule` in `router.py` inspects the decorated function signature and binds:

- path parameters such as `{channels}`;
- query parameters by name;
- `bytes` request bodies;
- JSON body wrappers;
- the whole `Request`;
- `WebSocket` and `EventStream`;
- path list or query dict.

The router can include sub-apps. Each component is itself a `slowlette.App`, so components contribute their own routes.

## Response merging

Slowlette dispatch does not stop at the first matching handler. It walks the component tree, collects all matching responses, then merges them from bottom to top.

Default merge behavior in `Response.merge_response()`:

- Higher status code wins.
- Equal status code merges content.
- Dict content is deep-merged.
- List content is appended.
- String content is appended with a newline.

SlowDash relies on this for aggregate endpoints:

- `/api/config` is assembled from multiple component `public_config()` responses.
- `/api/channels` can combine channels from multiple sources.
- `/api/data/{channels}` can merge data-source results with current-data caches.

Some components return custom `Response` subclasses whose `merge_response()` method modifies the downstream response. For example, current-data cache components add current values after data-source responses have been produced.

# Project Configuration Flow

`Project` in `sd_project.py` is responsible for discovering and loading the project configuration.

Configuration sources:

1. Explicit `--project-dir` or `--project-file`.
2. `SLOWDASH_PROJECT`.
3. Parent-directory search for `SlowdashProject.yaml`.
4. Environment-based initial data source via `SLOWDASH_INIT_DATASOURCE_URL`.

The project file must contain a `slowdash_project` dictionary. During loading, `Substitution` processes strings containing:

```text
${VARIABLE}
${VARIABLE-default}
${VARIABLE:-default-like-empty-is-null}
$(COMMAND)
$$
```

After loading:

- Missing `name` and `title` are filled.
- `system` defaults to `{}`.
- `authentication.key` becomes `project.auth_list`.
- `system.our_security_is_perfect` controls `project.is_secure`.

`ConfigComponent` exposes public project metadata through `/api/config`, but avoids publishing raw project configuration because it can contain secrets.

`project.mesh_url` comes from `slowdash_project.mesh.url`. If it is absent and a server port is available, it defaults to `slowmq://{hostname}:{port}`. `Mesh.connect()` can select NATS, MQTT, Redis, and RabbitMQ transports as well as SlowMQ. A `Mesh` without a URL uses local pub/sub.

# Built-In Server Components

## `Component` and `PluginComponent`

`Component` is the base class for server components. It provides:

- `self.app`
- `self.project`
- a default `/api/config` route that returns `public_config()`

`PluginComponent` builds component plugins from project config:

1. Read `project.config[component_type]` or plural form.
2. Normalize a single node into a list.
3. Resolve plugin file and class names.
4. Load plugin modules from `app/plugin`.
5. Instantiate plugin classes.
6. Include each plugin as a Slowlette sub-app.

When the app is not async, `_NoAsync` plugin files are preferred when available.

## `ConfigComponent`

Main responsibilities:

- Expose `/api/config`.
- List and load project `config/*-*.*` content.
- Serve config files when allowed.
- Manage transient content, such as generated plot content.

The `/api/config/contentlist` and `/api/config/content/{filename}` endpoints are used by UI components to discover dashboards, plots, cruises, and other user content.

## `DataSourceComponent` and `DataSource`

`DataSourceComponent` is a plugin-backed component for data sources.

Each `DataSource` plugin provides routes:

```text
GET /api/channels
GET /api/data/{channels}
GET /api/blob/{channel}
startup
shutdown
```

The base `DataSource` class supports both sync and async plugin implementations:

```text
initialize()       -> aio_initialize()
finalize()         -> aio_finalize()
get_channels()     -> aio_get_channels()
get_timeseries()   -> aio_get_timeseries()
get_object()       -> aio_get_object()
get_blob()         -> aio_get_blob()
```

The data query flow is:

```text
GET /api/data/{channels}
    |
    v
parse length/to/resample/reducer/filler/envelope/prior_data
    |
    v
aio_get_timeseries(...)
aio_get_object(...)
    |
    v
merge time-series and object results into one dict
```

The `DataSource.resample()` helper aligns time-series data into bins and supports reducers such as `last`, `mean`, `median`, `min`, `max`, `count`, and `sem`.

## `ExportComponent`

`ExportComponent` loads export plugins from project config.

It always ensures default export support:

- CSV export if no CSV export is configured.
- Notebook export if neither Notebook nor Jupyter export is configured.

Actual export routes are provided by the export plugins.

## `UserModuleComponent`

`sd_usermodule.py` provides an in-process Python extension mechanism for SlowDash.

User modules are loaded from project configuration and run in a `UserModuleThread`. The module can define lifecycle callbacks:

```text
_setup(app, params) or _setup(app) or _setup()
_initialize(params) or _initialize()
_run()
_loop()
_finalize()
```

User modules can also provide API handlers, content, HTML, layouts, channel/data hooks, and control commands depending on which functions they define.

The user-module thread normally uses its own event loop. It can optionally use the main event loop only when `_run()` and `_loop()` are async-compatible.

## `TaskComponent`

`sd_task.py` provides HTTP proxies for Mesh tasks and manages locally launched task processes. It replaces the removed `sd_taskmodule.py` rather than continuing its in-process thread execution model.

Main routes:

```text
GET  /api/task/catalog
GET  /api/task/status
POST /api/task/control/{taskname}
POST /api/control
GET  /api/channels
GET  /api/data/{*}
GET  /api/config/contentlist
GET  /api/config/content/{filename}
GET  /api/config/file/{filename}
```

- Builds a catalog from `task` / `tasks` configuration and `config/slowtask-*.py`. The default configured command is `slowdash-task <file_path> --name=<name>`, with the Mesh URL and JSON parameters added. `auto_start` (or the compatibility name `auto_load`) launches tasks using `subprocess.Popen`.
- Subscribes to `sd.task.spec.>`, `sd.task.exit.>`, `sd.task.heartbeat.>`, and `sd.task.life_event.>` and maintains `TaskProxy` objects by `mesh_id`. Publishing `sd.task.control.introduce` requests task specifications, so independently launched tasks can also register.
- `TaskFunctionProxy` prepares RPC arguments using the advertised argument specification. `TaskVariableProxy` reads values with `mesh.remote_node('<task>.<variable>')`.
- Task-control actions are `start`, `stop`, `kill`, and `purge`. `stop` calls the `<task>._sd_stop` RPC; `kill` acts on child processes tracked by this server; `purge` publishes exit notifications to remove registrations.
- Exported control nodes become channels and are read remotely for data requests covering the current time. Task content is exposed through configuration/content APIs using the `<task>._sd_get_content` RPC.

`slowdash-task.py` finds and runs a `Tasklet` in the script. If none is present, it creates `Tasklet(use_oldstyle_callbacks=True)` to load legacy callbacks. It connects standard I/O and logging to Mesh from script-loading time and uses `RetainerAutocide` to handle parent-process death.

### Task identity and lifecycle

A task name (for example, `sensor`) is an RPC namespace; `mesh_id` identifies a connected Mesh instance. `Mesh.connect()` constructs it from the name, hostname, PID, and a process-local sequence number. Task records are indexed by `mesh_id`, but RPC requests go to `sd.rpc.<taskname>`, so multiple tasks sharing a name can receive a request. Use unique names for ordinary task control.

The catalog describes launchable scripts, the task table describes tasks that have advertised specifications, and the process table tracks children launched by this server. An independently launched task can register through Mesh without its PID being owned by the server. `kill` targets tracked child processes; `purge` removes registrations. Restarting a task currently requires separate stop/start operations.

```text
TaskComponent.post_startup
  -> subscribe to task notifications
  -> start Mesh and request introductions
  -> load catalog and launch auto_start processes

slowdash-task process
  -> load script and bind Tasklet to ControlSystem
  -> connect Mesh / standard I/O / logging
  -> publish task specification
  -> run initialize callbacks
  -> publish updated specification
  -> run scheduled callbacks and heartbeat loop
  -> on stop: publish exit, cancel callbacks, run finalizers, close connections
```

Heartbeats are sent from the `Tasklet` main loop about every five seconds by default. The server calls `_check_task_heartbeats()` during operations such as channel queries and task control, allowing roughly five seconds beyond the advertised expiration. This is not an independent continuous monitoring thread. A missing heartbeat does not prove process exit; it can also indicate a blocked task event loop.

### Minimal task configuration

This example assumes SlowDash is running on port 18881 with its built-in SlowMQ available. The configured Mesh URL must point to a running broker.

```yaml
slowdash_project:
  name: MeshExample
  mesh:
    url: slowmq://localhost:18881
  task:
    - name: sensor
      file_path: config/slowtask-sensor.py
      auto_start: true
```

Contents of `config/slowtask-sensor.py`:

```python
from slowpy.mesh import Tasklet, DataPacket

task = Tasklet()
temperature = 12.3

@task.mesh.export
async def set_temperature(value: float):
    global temperature
    temperature = value
    return temperature

@task.loop(interval=1)
async def publish_temperature():
    await task.mesh.aio_publish(
        'data.stream', DataPacket(temperature, tag='temperature')
    )

if __name__ == '__main__':
    task.run(name='sensor', mesh_url='slowmq://localhost:18881')
```

When loaded by `slowdash-task`, the existing `task` is detected and executed through `run_module()`. When run directly with Python, the `__main__` block calls `task.run()`. This example streams the `temperature` channel and exposes `sensor.set_temperature` as an RPC function; it does not export a control node.

```text
POST /api/control
Content-Type: application/json

{"sensor.set_temperature()": null, "value": 20.0}
```

The command name is a JSON key; other fields supply arguments. For inclusion in the task specification, annotate arguments with `int`, `float`, `str`, or `bool`, or provide defaults from which these types can be inferred. The implementation uses this information to construct the specification and convert arguments on the server.

## `UserHtmlComponent`

`sd_userhtml.py` serves user-provided HTML and related content. It also redirects or maps user URLs to internal config/content APIs.

This lets project-specific UI pages live in the project configuration/content area without changing the core server.

## `WebMeshComponent`

`sd_webmesh.py` bridges Mesh and browser clients. The current-data cache role of the removed `sd_mesh.py` is now implemented by `DataCache` and merge-response classes in this file. Browser delivery uses SSE.

```text
SSE  /event/webmesh/attach
POST /api/webmesh/subscribe
POST /api/webmesh/unsubscribe
POST /api/webmesh/publish/{topic}
GET  /api/channels
GET  /api/data/{*}
```

It subscribes to `data.>`, `form.>`, task life-event/heartbeat/stdout topics, and `log.>`. It caches data and queues matching messages for each subscribed browser client. The SSE `register` event returns a `client_id`; `message` events contain `subscribed_topic`, `headers`, and `body`. Each client queue holds at most 10 messages; a full queue causes that client to be detached.

Browser subscriptions use `data.*.<channel>`, form topics such as `form.<form>.>`, and the fixed topic list in the code. Delivery currently follows the topic normalization in `_subscribe_mesh()`, not a general-purpose wildcard matcher. `unsubscribe` removes all subscriptions for the specified client.

`ChannelMergerResponse` adds missing streamed channels with `streaming: True`. `DataMergerResponse` fills data only when another response has not provided that channel and the cached `t` is a single number within the requested time range. It does not overwrite existing channel data or combine time-series arrays.

### Browser connection sequence

1. Open `/event/webmesh/attach` with `EventSource`.
2. Read `client_id` from the JSON in the `register` event.
3. POST JSON such as `{"client_id":"...","topic":"data.*.temperature"}` to `/api/webmesh/subscribe`. This route takes `client_id` from the body.
4. Decode each `message` event and display channel data from `body`. `headers.topic` is the original topic; `subscribed_topic` is the topic normalized for browser subscription matching.
5. To remove all subscriptions, POST to `/api/webmesh/unsubscribe?client_id=...`. Disconnecting the SSE stream also removes its queue and subscriptions.

The client in `app/site/slowjs/control.mjs` maps ordinary channels to `data.*.<channel>` and treats names starting with `@mesh:` as topics after removing that prefix. On errors it recreates the connection and resubmits subscriptions after registering the new `client_id`.

Neither attaching an SSE connection nor subscribing replays cached values. Use `/api/data` or registry reads for initial state. WebMesh queues deliver live messages; they are not persistent storage for replaying messages missed during disconnection.

## `SlowMQComponent`

`sd_slowmq.py` provides a built-in websocket pub/sub service.

Main route:

```text
WEBSOCKET /ws/slowmq
```

Each connected client has:

- a client id;
- an optional name;
- a websocket;
- zero or more topic-pattern subscriptions.

Messages contain headers. The header `action` determines whether the message is a publish, subscribe, or unsubscribe operation.

Topic patterns are dot-separated and support:

- `*` for exactly one token;
- `>` for zero or more trailing tokens, only as the final token.

SlowMQ is the WebSocket broker used as a Mesh transport; WebMesh provides browser-facing SSE delivery. The `AsyncSlowMQ` control node connects to this broker. Subscribe requests receive acknowledgements with `reply_to` matching the request's `message_id`. Disconnects remove subscriptions, and clients with five consecutive send failures are removed. Statistics and subscription counts are exposed under `slowmq` in `/api/config`.

### Message format and delivery

SlowMQ WebSockets carry JSON with `headers` and `data`. Mesh subscription callbacks receive `(headers, body)`, and WebMesh SSE delivers the payload in a field named `body`. The payload therefore has different field names at these boundaries. A scalar publication looks like this (with an illustrative timestamp):

```json
{
  "headers": {"topic": "data.stream.temperature"},
  "data": {"temperature": {"t": 1780000000.0, "x": 12.3}}
}
```

An omitted `action` means publish. `DataPacket(tag='temperature', ...)` uses the tag as both a topic suffix and a channel name in the body. `t` is a UNIX timestamp when `start` is absent, or an offset in seconds when `start` is supplied. Time-series records use an array for `t` and are excluded from WebMesh's HTTP cache fallback.

`AsyncSlowMQNode` shares a publishing WebSocket and opens a subscription WebSocket for each topic filter. The broker forwards messages to currently connected subscribers. It provides neither persistent message history nor an application-level acknowledgement that a published message has been processed. Subscription acknowledgements and RPC replies are separate mechanisms.

## `MeshRegistryComponent`

`Registry` in `sd_mesh_registry.py` stores values, revisions, and update times under dot-separated keys. `MeshRegistryComponent` exports `set`, `get`, `keys`, and `delete` RPCs under the Mesh name `sd_mesh_registry`. Clients use `mesh.registry.aio_set()` / `aio_get()` / `aio_keys()` / `aio_delete()`.

```text
GET /api/registry/keys/{path}
GET /api/registry/value/{key}
GET /api/data/{*}                 # @registry:<key> channels
GET /api/log
```

- A key ending in `>` addresses a subtree. `with_meta` returns metadata; `cas_revision` supports compare-and-set checks on individual updates and deletes. Subtree writes do not implement CAS.
- Stores the SlowDash URL in `server.url`, which `Tasklet` uses to discover the HTTP helper's endpoint.
- Subscribes to `>` and retains the latest message body under `pubsub.<topic>`, excluding topics starting with `sd.rpc`. This registry is separate from WebMesh's channel cache.
- Treats `pubsub.form.` and subtrees loaded from `registry-*.json` in the working directory as persistent, saving them when values are set. It does not persist every key.
- Keeps `log.>` records in memory and returns them as a table through `/api/log`. Data channel names beginning with `@registry:` expose registry values through `/api/data`.

### Choosing where state lives

| Location | Contents | Read path | Lifetime |
|---|---|---|---|
| WebMesh `DataCache` | Latest streamed channel records and types | `/api/channels` and `/api/data` fallback | Server process memory |
| Mesh `Registry` | Shared keys and latest pub/sub bodies | Registry RPC, `/api/registry/*`, `@registry:` | Mainly memory; selected subtrees saved as JSON |
| Exported task nodes | Current values managed by a task | Node RPC and `TaskComponent` data API | Depends on task/device |
| `slowpy.store` / data sources | Stored time series and objects | Data-source `/api/data` | Depends on storage backend |

To retain published data as history, a task or subscriber must explicitly call a writer such as `DataStore.append()`. Publishing to Mesh alone does not store data in a database.

Registry examples:

- `mesh.registry.aio_get('pubsub.form.settings.>')`: retrieve the latest messages for the settings form as a subtree.
- `mesh.registry.aio_get('state.run', with_meta=True)`: retrieve `key`, `value`, `revision`, and `updated`.
- `mesh.registry.aio_set('state.run', 'running', cas_revision=revision)`: update only if the previously read revision still matches; return `None` on mismatch.

Use `await` for these asynchronous calls. Revisions detect conflicts within the current registry; metadata is not restored when JSON files are loaded. Also, the current `delete()` removes an in-memory entry without rewriting its persistent file.

## Other components

Other server components include:

- `ConsoleComponent`: legacy console capture implementation, currently not included by `App`.
- `MiscApiComponent`: miscellaneous utility APIs.
- `BlobStorage_File`: file-backed blob storage used by data sources.

# Plugin Architecture

Plugins are normal Python modules under `app/plugin`. They are loaded dynamically by filename and class name.

For data sources:

```yaml
slowdash_project:
  data_source:
    type: SQLite
    parameters:
      ...
```

resolves to:

```text
datasource_SQLite.py
DataSource_SQLite
```

For exports:

```yaml
slowdash_project:
  export:
    type: CSV
```

resolves to:

```text
export_CSV.py
Export_CSV
```

`PluginComponent` also merges the nested `parameters` dictionary into the root parameter dictionary by default. This lets plugin constructors use a flattened parameter view.

# Data Query Communication Flow

```text
Browser or client
    |
    v
GET /api/channels
GET /api/data/{channels}?length=...&to=...
    |
    v
Slowlette dispatch -> component tree
    |
    +-- MeshRegistryComponent: @registry:<key> values
    +-- UserModuleComponent: user hooks
    +-- WebMeshComponent: streamed-data cache merge response
    +-- DataSourceComponent: stored data
    +-- TaskComponent: remote exported control nodes
    |
    v
Slowlette response merge -> JSON response
```

The `/api/data` response can involve stored data, current values from remote task nodes, WebMesh's streamed-data cache, and registry values. `TaskComponent` and `WebMeshComponent` use `/api/data/{*}` to allow `/` in channel names.

WebMesh only fills missing channels with cached single-timestamp records. Separately, `TaskComponent.DataMergerResponse` can append a newer current value to a scalar or the end of a time series. These are distinct merge implementations, and the final response also depends on component include order.

# Publish and Current-Data Flow

```text
Tasklet / Mesh producer
    |  Mesh.aio_publish('data.stream', DataPacket(..., tag='channel'))
    v
Mesh transport / broker: data.stream.channel
    |
    +-- WebMeshComponent -> DataCache
    |                    -> attached browser clients (SSE)
    |
    +-- MeshRegistryComponent -> pubsub.data.stream.channel
```

HTTP clients can publish a JSON body through `POST /api/webmesh/publish/{topic}`. The `publish <topic>(...)` form of `POST /api/control` also maps to pub/sub. Form updates use `FormPacket` and `form.<form>.<element>`; the registry retains their latest values under `pubsub.form`.

`ControlSystem.aio_publish()` and `stream()` also send `data.stream.<name>` through the bound `Tasklet`'s Mesh. Streamed data and exported control nodes accessed through RPC are separate paths.

# Control Flow

```text
POST /api/control
    |
    v
TaskComponent.execute_command() -> MeshRequest
    |
    +-- publish <topic>(...) -> Mesh.aio_publish()
    |
    +-- <task>.<function>(...) -> TaskProxy.process_command()
                                  -> TaskFunctionProxy.match_kwargs()
                                  -> Mesh.aio_call_many()
                                  -> sd.rpc.<task>
                                  -> exported function in task process
                                  -> sd.rpc_reply.<caller_mesh_id>
                                  -> HTTP reply
```

`MeshRequest` parses command names and parameters. The old `await`, `reentrant`, `async`, and `parallel` prefixes are stripped with an obsolete-modifier warning for compatibility; they no longer select an execution mode. The RPC receiver calls the exported function and awaits a coroutine result. Replies contain `status`, `message`, and `return_value` and are matched to calls using correlation IDs.

Control nodes are accessed with `mesh.remote_node('<task>.<variable>').aio_get()` / `aio_set()`. These use the `<task>._sd_node_call` RPC to invoke the exported node's `aio_get()` / `aio_set()`. User modules can still participate through their own control hooks.

### RPC replies and execution model

Requests carry `module`, `function`, `sender_id`, `reply_to`, `correlation_id`, and `message_id` headers, with `args` / `kwargs` in the body. `Mesh` keeps a reply queue for each correlation ID; `aio_call_many()` waits for the requested reply count or a timeout. `TaskProxy` function calls request one reply with a five-second timeout. `aio_call()` checks the reply status and returns `return_value`, whereas `aio_call_many()` returns reply records for the caller to inspect.

A Mesh instance's RPC receive loop waits for a function to finish before handling the next request. Using `async def` does not make that receive loop run multiple RPCs concurrently. Synchronous functions execute directly on the event loop and are not automatically moved to worker threads. Keep RPC handlers short, for example by putting ongoing work in Tasklet loops.

A caller-side timeout does not mean the remote function was never executed or was cancelled. Retrying an operation that changes state must account for possible duplicate execution.

# SlowPy Library Role

SlowPy is used by both server-side components and user code.

## Mesh communication and Tasklet

`Mesh` layers topic conversion, callback subscriptions, and RPC over asynchronous pub/sub nodes in `control/`. Applications normally use `.`, `*`, and `>` topic syntax, which is converted to the transport's separators and wildcards. External brokers also require the corresponding control module's dependencies.

Main APIs:

- `aio_start()` / `aio_close()`: start and close connections and background handlers.
- `publisher()` / `subscriber()`: access pub/sub as control nodes.
- `aio_publish()`, `aio_subscribe()`, and `@mesh.on(...)`: send and receive messages. `publish()` schedules publishing on a running event loop, so it requires one.
- `@mesh.export` or `mesh.export(name, function_or_node)`: expose functions and control nodes.
- `aio_call()` returns one RPC return value; `aio_call_many()` returns a list of reply records. Requests use `sd.rpc.<module>` and replies use `sd.rpc_reply.<mesh_id>`.
- `remote_node()` and `registry`: access remote control nodes and the shared registry.

`DataPacket` converts scalar values, data elements, field dictionaries, and `TimeSeries` into Mesh bodies and appends `tag` to the topic when present. `FormPacket` generates `form.<form>.<element>` with a body containing `form`, `element`, and `value`.

```python
import asyncio
from slowpy.mesh import Mesh, DataPacket

async def main():
    mesh = Mesh('slowmq://localhost:18881', name='producer')
    await mesh.aio_start()
    try:
        await mesh.aio_publish('data.stream', DataPacket(12.3, tag='temperature'))
    finally:
        await mesh.aio_close()

asyncio.run(main())
```

`Tasklet` owns a Mesh and provides the task runtime. Callbacks are registered with `initialize()`, `finalize()`, `once()`, `loop()`, `schedule()`, and `content()` decorators and run through `run()` or the CLI's `run_module()`. Task specifications describe functions, argument types, control nodes, content, and standard I/O. Tasklets publish specifications, heartbeats, and exit notifications under `sd.task.*` and respond to `sd.task.control.introduce`.

Compatibility mode discovers `_initialize`, `_finalize`, `_run`, `_loop`, HTML/layout callbacks, and public functions. Long-running work and loops should use async functions and async I/O so Mesh handlers and heartbeats can continue running.

For tasks, `MeshStdio` connects standard I/O to `sd.task.stdin.<mesh_id>` and `sd.task.stdout.<mesh_id>` (stderr shares the stdout topic by default). `MeshLogHandler` publishes Python logs under `log.>`. `Tasklet.dash` separately provides reads from SlowDash's HTTP API.

### Tasklet callbacks and execution boundaries

For the user-facing concepts and further examples, see [SlowMesh and SlowTask (Japanese)](SlowMesh_JP.md). SlowMesh is the communication layer (PubSub, RPC, and Registry); SlowTask is the independently running script; `Tasklet` is the adapter that supplies that script's lifecycle and Mesh connection. A standalone `Mesh` can communicate without becoming a managed task or publishing task specifications and heartbeats.

| Decorator | Runtime behavior |
|---|---|
| `@tasklet.initialize()` | Runs during initialization; a callback accepting an argument receives the task parameter dictionary. |
| `@tasklet.finalize()` | Runs during orderly shutdown, after running task callbacks are cancelled. |
| `@tasklet.once(delay=0)` | Runs once after initialization and the specified delay. |
| `@tasklet.loop(interval=1, ticks=None)` | Repeatedly runs a callback; an integer `ticks` supplies a periodic boolean argument, while a dictionary supplies named flags such as `tick.store`. |
| `@tasklet.schedule("08:00", use_utc=False)` | Runs on matching clock times; supports comma-separated `HH:MM` entries and `*` fields, using local time unless UTC is selected. |
| `@tasklet.content("config/html-status")` | Registers an on-demand content generator, fetched through the task's `_sd_get_content` RPC; it is not a periodic callback. |

Multiple callbacks can use the same decorator. Main callbacks are separate asyncio tasks, but share the event loop with Mesh communication and heartbeats. A single loop callback is awaited before its next invocation; missed intervals do not create overlapping invocations. Blocking I/O or `time.sleep()` in any callback blocks the whole event loop. Use asynchronous I/O and `await asyncio.sleep()` when a delay is needed. Finalizers are not guaranteed to run after a process kill or crash.

Project task `parameters` and the CLI's `--parameters` JSON option supply initialization parameters. This parameter dictionary is distinct from RPC arguments supplied later through `/api/control`. Content generators and exported control nodes are also distinct: generators return documents on demand, while nodes expose live values through remote get/set operations.

## Data object model

SlowPy provides Python objects that can be converted into SlowDash-compatible data:

- scalar values;
- `TimeSeries`;
- histograms;
- graphs;
- trends;
- trees;
- tables;
- matplotlib-derived data via `slowdashify`.

These objects are used by task/user code, storage writers, and APIs that publish current data.

### Creating and filling data objects

Data objects are created from the top-level `slowpy` package and populated incrementally, typically inside a task loop:

```python
import slowpy as slp

hist = slp.Histogram(100, 0, 10)         # 100 bins over [0, 10]
graph = slp.Graph(['channel', 'value'])

while not ControlSystem.is_stop_requested():
    value = device.read(...)
    hist.fill(value)
    graph.fill(channel, value)
```

Each object implements `to_json()`, which is how the same object can be published as current data (through `ControlSystem.stream()` / `aio_publish()`) or written to a data store. Trend helpers such as `slp.RateTrend` accumulate values over a moving window and produce a `TimeSeries` suitable for storage:

```python
rate_trend = slp.RateTrend(length=300, tick=10)
rate_trend.fill(time.time())
datastore.append(rate_trend.time_series('rate'))
```

## Control nodes

`ControlNode` in `slowpy/control/node.py` is the base abstraction for readable/writable control endpoints.

Main methods:

```text
set(value)
get()
aio_set(value)
aio_get()
has_data()
aio_has_data()
sleep()
aio_sleep()
wait()
aio_wait()
readonly()
writeonly()
```

The async methods delegate to sync methods by default. If `_is_thread_safe` is set, sync `get()` and `set()` calls can be run through `asyncio.to_thread()`.

### Building and using control-node chains

SlowPy maps every external system or device into a single control tree. Each node exposes `set()` and `get()`, and methods with noun-like names return child nodes. A chain of these accessors describes the logical path to a specific endpoint.

A typical starting point is a `ControlSystem` instance (or the shared `control_system` instance):

```python
from slowpy.control import ControlSystem
ctrl = ControlSystem()

# Build a node chain: Ethernet connection -> SCPI -> a specific command
device = ctrl.ethernet(host='192.168.1.43', port=5025)
Vout = device.scpi(append_opc=True).command('VOLT')
V    = device.scpi().command('MEAS:VOLT:DC')
```

Each call in the chain adds a branch:

- `ctrl.ethernet(...)` opens (or reuses) a TCP connection node.
- `.scpi()` returns a child node that holds SCPI configuration.
- `.command('VOLT')` binds the chain to a specific SCPI command.

Once a leaf node is built, `set()` writes and `get()` reads:

```python
Vout.set(10)        # sends SCPI "VOLT 10;*OPC?"
value = V.get()     # sends SCPI "MEAS:VOLT:DC?" and returns the reply
```

`ControlNode` also defines several shortcuts:

- `node(value)` is equivalent to `node.set(value)`.
- `node()` is equivalent to `node.get()`.
- `node <= value` performs `node.set(value)`.
- `float(node)`, `int(node)`, `str(node)`, and `print(node)` implicitly call `node.get()`.

The asynchronous equivalents are `await node.aio_set(value)` and `value = await node.aio_get()`, available on every node through the sync/async model described below.

Branches are added by plugins and are not limited to the root `ControlSystem`. A plugin can be loaded onto any node; for example, a protocol plugin loaded onto an Ethernet node creates a sub-branch that reuses the Ethernet node's `set()` (send) and `get()` (receive). For the full catalogue of built-in nodes (Ethernet/SCPI/Telnet, HTTP, Shell, Slowdash, Redis, and others) and their `set()` / `get()` semantics, see [Controls Script](ControlsScript.html).

Control modules under `slowpy/control/control_*.py` provide concrete device, network, message, shell, HTTP, datastore, and protocol integrations.

### Synchronous and asynchronous control modules

Most integrations are provided as a synchronous/asynchronous pair of modules, named `control_X.py` and `control_AsyncX.py`:

```text
control_HTTP.py      / control_AsyncHTTP.py
control_Redis.py     / control_AsyncRedis.py
control_RabbitMQ.py  / control_AsyncRabbitMQ.py
control_MQTT.py      / control_AsyncMQTT.py
control_Modbus.py    / control_AsyncModbus.py
control_Slowdash.py  / control_AsyncSlowdash.py
control_Dripline.py  / control_AsyncDripline.py
```

Some integrations exist in only one form:

- Synchronous only, such as `control_Ethernet.py`, `control_UDP.py`, `control_Serial.py`, `control_VISA.py`, `control_Shell.py`, `control_DataStore.py`, `control_LabJackU.py`, `control_NanotechMotor.py`, `control_Microphone.py`, and `control_DummyDevice.py`.
- Asynchronous only, such as `control_AsyncNATS.py`, `control_AsyncSlowMQ.py`, and `control_AsyncLocalPubsub.py`.

The two forms differ only in how the I/O methods are implemented:

- A synchronous module (for example `HttpNode` in `control_HTTP.py`) overrides `set()` / `get()` and uses blocking libraries such as `requests`.
- An asynchronous module (for example `AsyncHttpNode` in `control_AsyncHTTP.py`) overrides `aio_set()` / `aio_get()` and uses non-blocking libraries such as `httpx`.

Both forms subclass `ControlNode`, so they share the same node-tree model, child-node accessors, `readonly()` / `writeonly()` wrappers, and helper methods (`sleep()`, `wait()`, and their `aio_*` variants). Only the leaf I/O implementation changes.

### Node-tree registration

Each node class defines a classmethod `_node_creator_method()` that returns a factory function. `ControlNode.add_node()` injects this function as a method on a parent node class, and the function name becomes the accessor used to create child nodes. Synchronous and asynchronous variants usually expose different accessor names, for example:

```text
HttpNode       -> node.http(url)
AsyncHttpNode  -> node.async_http(url)
```

`ControlNode.import_control_module(name)` loads `control_<name>.py` from the current working directory or the `slowpy/control` directory, scans it for classes that define `_node_creator_method()`, and registers their accessors on the node class. `ControlSystem.__init__()` imports a default set of modules:

```text
Ethernet
HTTP
AsyncHTTP
Shell
DataStore
```

Additional modules are imported on demand from task or user code, for example `ControlSystem().import_control_module('Redis')`.

### Relationship to the async fallback

The base `ControlNode` already provides default `aio_set()` / `aio_get()` methods that delegate to the synchronous `set()` / `get()` (directly, or through `asyncio.to_thread()` when `_is_thread_safe` is set). A synchronous-only module can therefore still be used from async code. The dedicated `control_Async*.py` modules exist for cases where genuinely non-blocking I/O matters, such as long-lived network or message-broker connections. This mirrors the server-side `DataSource` sync/async dual methods and the `_NoAsync` data-source plugins described earlier.

## Data stores

SlowPy data stores provide write-side storage helpers.

`store/factory.py` maps URLs to implementations:

```text
postgresql:// -> DataStore_PostgreSQL
mysql://      -> DataStore_MySQL
sqlite://     -> DataStore_SQLite
influxdb2://  -> DataStore_InfluxDB2
redis://      -> DataStore_Redis
csv:///       -> DataStore_CSV
dump:///      -> DataStore_TextDump
```

`DataStore` supports:

```text
append(values, tag=None, timestamp=None)
update(values, tag=None, timestamp=None)
close()
```

Values can be scalars, dictionaries of fields, data elements, or `TimeSeries`.

### Writing data

A store is created directly from its class, or from a URL through `create_datastore_from_url()` in `store/factory.py`:

```python
from slowpy.store import DataStore_PostgreSQL

datastore = DataStore_PostgreSQL(
    'postgresql://postgres:postgres@localhost:5432/SlowTestData',
    table='SlowData'
)

while True:
    datastore.append(value, tag='voltmeter')      # a single value under a channel tag
    datastore.append({'ch00': v0, 'ch01': v1})    # a dict of channel/value pairs
```

`append()` adds a new time-series record, while `update()` overwrites the previous value so that only the latest is kept. This distinction matters for data-element objects such as histograms:

```python
datastore.append(hist, tag='spectrum')   # time-series of histograms (one per time point)
datastore.update(hist, tag='spectrum')   # keep only the latest histogram
```

For SQL stores, a "long format" with UNIX timestamps is used by default. A user-defined `TableFormat` can override the schema and insert statements when a different table layout is required.

# Slowlette Internals That Matter to SlowDash

Several SlowDash behaviors depend directly on Slowlette's design:

### Multiple handlers can answer the same route

Slowlette intentionally calls all matching handlers in the app tree. This is why many components can provide `/api/config`, `/api/channels`, or `/api/data/{channels}`.

### Response merging is part of the application model

The merged response is not just a convenience. It is how SlowDash builds aggregate API responses from independently developed components and plugins.

### Component order is meaningful

Because custom responses can merge later responses, `slowdash.py` include order is part of the runtime behavior.

### Internal API calls use the same router

`App.request()`, `request_config()`, `request_channels()`, and `request_data()` call `self.slowlette(...)` directly and use the same routing and response merging model as HTTP requests. Mesh pub/sub and RPC are a separate communication path.

# Summary of Main Flows

### Startup

```text
slowdash.py
  -> App
  -> Project
  -> sys.path / cwd setup
  -> include components
  -> ASGI/WSGI/CGI/CLI dispatch
  -> post_startup: Mesh connections, task discovery / auto-start
```

### API request

```text
HTTP request
  -> Slowlette server adapter
  -> Request
  -> Router
  -> matching component/plugin handlers
  -> Response list
  -> merged Response
  -> HTTP response
```

### Data read

```text
/api/data/{channels}
  -> data source plugins
  -> user hooks / remote task nodes / WebMesh cache / registry values
  -> merged JSON data
```

### Config read

```text
/api/config
  -> each component public_config()
  -> deep-merged JSON config
```

### Current data

```text
Mesh.aio_publish() / POST /api/webmesh/publish/{topic}
  -> Mesh transport / broker
  -> WebMesh cache and browser SSE
  -> registry pubsub cache
```

### Plugin loading

```text
project config
  -> PluginComponent
  -> app/plugin module lookup
  -> class lookup
  -> plugin instance
  -> Slowlette include
```

# Practical Development Notes

- When adding a new API component, subclass `Component` and include it from `slowdash.py`.
- When adding a new data source, subclass `DataSource` in a new `app/plugin/datasource_*.py` file.
- When adding a new exporter, add an `export_*.py` plugin.
- If an endpoint should aggregate with other components, return dict/list content and rely on response merging.
- If an endpoint should modify later component output, return a custom `slowlette.Response` subclass and override `merge_response()`.
- Avoid placing secrets in `public_config()`, because `/api/config` is exposed to clients.
- Be careful when changing component include order; it can change merge behavior.
- Use internal `App.request*()` helpers when server-side code should exercise the same route logic as external API clients.

- For a new Mesh task, use `Tasklet` and `mesh.export()` and run it through `slowdash-task` or an independent process.
- Keep browser delivery (WebMesh SSE), Mesh transport (SlowMQ or another broker), and shared state (Mesh registry) as separate responsibilities.
