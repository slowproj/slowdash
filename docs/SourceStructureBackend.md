---
title: Source Structure - Python Backend
---

This document describes the current SlowDash source structure and runtime flows as of the latest `develop` branch checked on 2026-06-01. It focuses on the existing implementation under `app/server`, `app/plugin`, `lib/slowpy`, and `lib/slowlette`.

It intentionally describes the current system, not planned future work.

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
    - user/task module API
    - export API
    - user HTML/content API
    - real-time/current-data helpers
    |
    v
Plugins and libraries
    - app/plugin data sources and exporters
    - slowpy data objects, control nodes, stores, client helpers
```

The central server object is `App` in `app/server/slowdash.py`. It subclasses `slowlette.App`, creates a `Project`, adjusts the runtime environment, then includes a list of SlowDash components into the Slowlette router.

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
- `sd_taskmodule.py`: current in-process task module system.
- `sd_userhtml.py`: user-provided HTML/content serving.
- `sd_console.py`: console/stdout capture.
- `sd_misc_api.py`: miscellaneous built-in API endpoints.
- `sd_mesh.py`: current-data cache and websocket attachment for selected topics.
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
- `middleware.py`: middleware support.

### `lib/slowpy`

SlowPy provides data types, control abstractions, storage writers, client helpers, and plotting helpers.

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

# Application Startup Flow

## Command-line or server startup

The main entry point is `app/server/slowdash.py`.

The normal startup sequence is:

1. Parse command-line options.
2. Create `App(project_dir, project_file, is_cgi, is_command, is_async)`.
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
ConsoleComponent
MeshComponent
UserModuleComponent
TaskModuleComponent
ConfigComponent
DataSourceComponent
UserHtmlComponent
ExportComponent
MiscApiComponent
SlowMQComponent
```

This order matters because Slowlette collects responses from multiple matching handlers and merges them. Earlier components can provide merge wrappers, and later components can provide content to be merged.

Notable ordering comments in the code:

- `ConsoleComponent` is first so it can capture stdout early.
- `MeshComponent` is before data sources so its cache merger can augment data-source replies.
- `UserModuleComponent` and `TaskModuleComponent` are before `DataSourceComponent` so user/task modules can participate in APIs and create data sources.

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
@slowlette.on_event('startup')
```

`PathRule` in `router.py` inspects the decorated function signature and binds:

- path parameters such as `{channels}`;
- query parameters by name;
- `bytes` request bodies;
- JSON body wrappers;
- the whole `Request`;
- `WebSocket`;
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

## `TaskModuleComponent`

`sd_taskmodule.py` is the current in-process task module system.

It extends the user-module mechanism and adds task command parsing, command execution, and `ControlSystem` integration.

Main routes include:

```text
GET  /api/control/task
POST /api/control
POST /api/control/task/{taskname}
GET  /api/channels
GET  /api/data/{channels}
POST /api/consume/current_data
```

Task command flow:

```text
POST /api/control
    |
    v
TaskModuleComponent.execute_command()
    |
    v
each TaskModule.process_command()
    |
    v
parse command name, arguments, await/reentrant flags
    |
    v
match namespace prefix/suffix
    |
    v
call task function immediately or in TaskFunctionThread
```

Exported control nodes are exposed as current channels and can be read through `/api/data/{channels}`. Incoming current-data messages can be used to set exported variables through `/api/consume/current_data`.

## `UserHtmlComponent`

`sd_userhtml.py` serves user-provided HTML and related content. It also redirects or maps user URLs to internal config/content APIs.

This lets project-specific UI pages live in the project configuration/content area without changing the core server.

## `MeshComponent`

`sd_mesh.py` maintains a cache of current data received through `/api/consume/current_data`.

Main roles:

- websocket attachment for selected topics;
- `/api/emit/{topic}` re-emission and websocket forwarding;
- current-data caching;
- `/api/channels` augmentation with cache-backed current channels;
- `/api/data/{channels}` augmentation with latest cache values.

This component is included before data sources so its custom response can merge cache data with downstream data-source responses.

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

## Other components

Other server components include:

- `ConsoleComponent`: captures console output for display or API use.
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

The most common read path is:

```text
Browser or client
    |
    v
GET /api/channels
GET /api/data/{channels}?length=...&to=...
    |
    v
Slowlette ASGI/WSGI dispatch
    |
    v
SlowDash component tree
    |
    +-- MeshComponent cache merge response
    +-- UserModuleComponent hooks
    +-- TaskModuleComponent current exports
    +-- DataSourceComponent plugins
    |
    v
Slowlette response merge
    |
    v
JSON response
```

For `/api/data/{channels}`, `DataSource` plugins return data in the SlowDash data model. Cache components can add current values if:

- the requested channel is cache-backed;
- the cached timestamp is inside the requested time window;
- the existing response is absent or older than the cached value.

# Write, Emit, and Current-Data Flow

Current-data updates can enter SlowDash through:

```text
POST /api/emit/{topic}
POST /api/consume/current_data
internal app.request_emit(topic, message, sender=...)
```

Typical flow:

```text
producer
    |
    v
/api/emit/current_data
    |
    v
app.request('/consume/current_data', data)
    |
    +-- MeshComponent.cache_current_data()
    +-- TaskModuleComponent.set_variable()
    |
    v
websocket forwarding to attached clients
```

The `sender` parameter is used to avoid reflecting a task's own published value back into the same task variable path.

# Control Flow

Control commands use `/api/control`.

Current in-process task flow:

```text
POST /api/control
    |
    v
TaskModuleComponent.execute_command()
    |
    v
TaskModule.process_task_command()
    |
    +-- parse "await", "reentrant", "async", "parallel" prefixes
    +-- parse function arguments
    +-- match task namespace
    +-- bind parameters using Python function signature
    |
    v
execute function synchronously, await it, or run it in a command thread
```

User modules can also participate in command processing through their own hooks, depending on the functions they define.

# SlowPy Library Role

SlowPy is used by both server-side components and user code.

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

Control modules under `slowpy/control/control_*.py` provide concrete device, network, message, shell, HTTP, datastore, and protocol integrations.

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

# Slowlette Internals That Matter to SlowDash

Several SlowDash behaviors depend directly on Slowlette's design:

### Multiple handlers can answer the same route

Slowlette intentionally calls all matching handlers in the app tree. This is why many components can provide `/api/config`, `/api/channels`, or `/api/data/{channels}`.

### Response merging is part of the application model

The merged response is not just a convenience. It is how SlowDash builds aggregate API responses from independently developed components and plugins.

### Component order is meaningful

Because custom responses can merge later responses, `slowdash.py` include order is part of the runtime behavior.

### Internal API calls use the same router

`App.request()`, `request_config()`, `request_channels()`, `request_data()`, and `request_emit()` call `self.slowlette(...)` directly. Internal producers and consumers therefore use the same routing and response merging model as external HTTP clients.

# Summary of Main Flows

### Startup

```text
slowdash.py
  -> App
  -> Project
  -> sys.path / cwd setup
  -> include components
  -> ASGI/WSGI/CGI/CLI dispatch
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
  -> optional user/task/current-data additions
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
/api/emit/current_data
  -> /api/consume/current_data
  -> cache update and variable update hooks
  -> websocket forwarding where applicable
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
