---
title: ソース構造 - Python バックエンド
---

この文書は，2026-06-01 に確認した最新 `develop` ブランチ時点の SlowDash のソース構造と実行時フローを説明するものです．対象は，既存実装の `app/server`，`app/plugin`，`lib/slowpy`，`lib/slowlette` です．

ここでは現在のシステムだけを説明し，将来計画については扱いません．

# 全体構造

SlowDash は主に 4 つの Python レイヤーで構成されています．

```text
Client / CLI / CGI
    |
    v
Slowlette
    - ASGI/WSGI アダプタ
    - URL ルーティング
    - request 引数バインディング
    - response merge
    |
    v
SlowDash server components
    - project/config 処理
    - data source API
    - user/task module API
    - export API
    - user HTML/content API
    - real-time/current-data 補助機能
    |
    v
Plugins and libraries
    - app/plugin の data source / exporter
    - slowpy の data object，control node，store，client helper
```

中心となる server object は `app/server/slowdash.py` の `App` です．`App` は `slowlette.App` を継承し，`Project` を作成し，実行環境を整えたうえで，SlowDash の各 component を Slowlette router に include します．

# 主要ディレクトリ

### `app/server`

このディレクトリには，SlowDash の web application と組み込み API component が入っています．

主要ファイル:

- `slowdash.py`: application entry point，command-line entry point，component assembly，内部 API helper．
- `slowdash_wsgi.py` と `slowdash.cgi`: WSGI/CGI entry point．
- `sd_project.py`: project 探索，YAML 読み込み，環境変数/コマンド置換，公開 project metadata．
- `sd_component.py`: component と plugin-backed component の base class．
- `sd_config.py`: `/api/config`，config file/content API，transient content．
- `sd_datasource.py`: data source plugin base class と `/api/channels`，`/api/data`，`/api/blob` route．
- `sd_datasource_SQL.py`，`sd_datasource_TableStore.py`，`sd_dataschema.py`: data source 共通 helper．
- `sd_blobstorage.py`: blob storage helper．
- `sd_export.py`: export plugin component．
- `sd_usermodule.py`: in-process user module 拡張システム．
- `sd_taskmodule.py`: 現行の in-process task module システム．
- `sd_userhtml.py`: user-provided HTML/content 配信．
- `sd_console.py`: console/stdout capture．
- `sd_misc_api.py`: その他の組み込み API endpoint．
- `sd_mesh.py`: current-data cache と一部 topic への websocket attachment．
- `sd_slowmq.py`: 組み込み websocket-based pub/sub component．
- `sd_version.py`: version string．

### `app/plugin`

このディレクトリには，`PluginComponent` により読み込まれる plugin module が入っています．

Data source plugin:

- `datasource_CSV.py`
- `datasource_SQLite.py`
- `datasource_PostgreSQL.py`，`datasource_PostgreSQL_NoAsync.py`
- `datasource_MySQL.py`，`datasource_MySQL_mysqlclient.py`，`datasource_MySQL_NoAsync.py`
- `datasource_InfluxDB2.py`
- `datasource_Redis.py`，`datasource_Redis_NoAsync.py`
- `datasource_MongoDB.py`
- `datasource_CouchDB.py`
- `datasource_Honeybee.py`
- `datasource_Dummy.py`
- `datasource_SystemResource.py`
- `datasource_YAML.py`

Export plugin:

- `export_CSV.py`
- `export_Notebook.py`
- `export_Jupyter.py`

Plugin の file name と class name は規約で決まります．たとえば data source type が `SQLite` の場合は，次に対応します．

```text
app/plugin/datasource_SQLite.py
DataSource_SQLite
```

### `lib/slowlette`

Slowlette は SlowDash が使用する小さな web framework です．

主要ファイル:

- `app.py`: `App` と `Slowlette` application class．
- `router.py`: decorator，path matching，argument binding，sub-app dispatch，response merge．
- `server.py`: ASGI/WSGI dispatch と開発用 server helper．
- `request.py`: parse 済み HTTP request object．
- `response.py`: response object，content merge，file response．
- `model.py`: JSON request-body wrapper．
- `websocket.py`: websocket wrapper と connection close 処理．
- `middleware.py`: middleware support．

### `lib/slowpy`

SlowPy は data type，control abstraction，storage writer，client helper，plotting helper を提供します．

主要領域:

- Top-level data object:
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
- Data store:
  - `store/store.py`
  - `store/factory.py`
  - `store/store_SQL.py`
  - `store/store_CSV.py`
  - `store/store_HDF5.py`
  - `store/store_InfluxDB2.py`
  - `store/store_Redis.py`
- Client helper:
  - `slowfetch.py`

公開 top-level `slowpy` package は，`Histogram`，`Graph`，`Trend`，`Tree`，`Table`，`TimeSeries`，`SlowFetch`，`slowdashify`，`slowplot` などのよく使う data object/helper を export します．

# Application Startup Flow

## Command-line または server startup

主な entry point は `app/server/slowdash.py` です．

通常の startup sequence:

1. command-line option を parse する．
2. `App(project_dir, project_file, is_cgi, is_command, is_async)` を作成する．
3. `App` が `Project` を作成する．
4. `Project` が SlowDash system directory と project directory を探す．
5. `Project` が `SlowdashProject.yaml` を読み込む．設定によっては environment variable から初期 data source config を作る．
6. project directory がある場合，`App` は process working directory を project directory に移動する．
7. `App` は system plugin directory，project directory，project の `config` directory を `sys.path` に追加する．
8. `App` が全 built-in component を Slowlette router に include する．
9. 選択された mode に応じて，ASGI，WSGI，CGI，または command-line internal request として実行される．

## Component include order

`slowdash.py` は component を次の順序で include します．

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

この順序は重要です．Slowlette は複数の matching handler から response を集めて merge するため，先に include された component が merge wrapper を返し，後続 component の response を加工することがあります．

コード中の重要な意図:

- `ConsoleComponent` は stdout を早期に capture するため最初に include される．
- `MeshComponent` は data source response に cache を重ねるため，data source より前に include される．
- `UserModuleComponent` と `TaskModuleComponent` は user/task module が API や DB 作成に関与できるよう，`DataSourceComponent` より前に include される．

# Slowlette Routing and Response Model

## Request flow

ASGI の場合:

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

WSGI の場合:

```text
WSGI server
    |
    v
slowlette.server.dispatch_wsgi()
    |
    v
Request -> asyncio.run(router.dispatch()) -> WSGI response
```

Slowlette は受信 URL を `Request` に変換します．

- `Request.path`: decode 済み path component．
- `Request.query`: decode 済み query dictionary．
- `Request.headers`: server layer から渡される header dictionary．
- `Request.body`: raw body，または internal dispatch 用の Python object．

## Decorator と argument binding

Handler は次のような decorator で宣言されます．

```python
@slowlette.get('/api/channels')
@slowlette.post('/api/control')
@slowlette.websocket('/ws/slowmq')
@slowlette.on_event('startup')
```

`router.py` の `PathRule` は decorated function の signature を調べ，次を bind します．

- `{channels}` のような path parameter．
- 名前で一致する query parameter．
- `bytes` request body．
- JSON body wrapper．
- request 全体を表す `Request`．
- `WebSocket`．
- path list または query dict．

Router は sub-app を include できます．各 component はそれ自体が `slowlette.App` なので，component ごとに route を追加できます．

## Response merging

Slowlette dispatch は最初に一致した handler で止まりません．Component tree を歩き，すべての matching response を集め，下から上に merge します．

`Response.merge_response()` の default merge behavior:

- status code が大きい response が勝つ．
- status code が同じ場合は content を merge する．
- dict content は deep merge される．
- list content は append される．
- string content は newline 付きで append される．

SlowDash は aggregate endpoint のためにこの仕組みに依存しています．

- `/api/config` は複数 component の `public_config()` response から組み立てられる．
- `/api/channels` は複数 source からの channel を combine できる．
- `/api/data/{channels}` は data-source result と current-data cache を merge できる．

一部 component は `merge_response()` を override した custom `Response` subclass を返します．たとえば current-data cache component は，data-source response が生成された後に current value を追加します．

# Project Configuration Flow

`sd_project.py` の `Project` は project configuration の探索と読み込みを担当します．

Configuration source:

1. 明示的な `--project-dir` または `--project-file`．
2. `SLOWDASH_PROJECT`．
3. 親 directory 方向への `SlowdashProject.yaml` 探索．
4. `SLOWDASH_INIT_DATASOURCE_URL` による environment-based initial data source．

Project file は `slowdash_project` dictionary を含む必要があります．読み込み時に，`Substitution` が次の形式の文字列置換を処理します．

```text
${VARIABLE}
${VARIABLE-default}
${VARIABLE:-default-like-empty-is-null}
$(COMMAND)
$$
```

読み込み後:

- `name` と `title` がなければ補完される．
- `system` は `{}` が default になる．
- `authentication.key` は `project.auth_list` になる．
- `system.our_security_is_perfect` は `project.is_secure` を制御する．

`ConfigComponent` は `/api/config` で公開 project metadata を返します．ただし raw project configuration は secret を含みうるため，そのまま公開しません．

# Built-In Server Components

## `Component` and `PluginComponent`

`Component` は server component の base class です．次を提供します．

- `self.app`
- `self.project`
- `public_config()` を返す default `/api/config` route

`PluginComponent` は project config から component plugin を構築します．

1. `project.config[component_type]` または plural form を読む．
2. 単一 node を list に正規化する．
3. plugin file と class name を解決する．
4. `app/plugin` から plugin module を読み込む．
5. plugin class を instantiate する．
6. 各 plugin を Slowlette sub-app として include する．

App が async でない場合，利用可能なら `_NoAsync` plugin file が優先されます．

## `ConfigComponent`

主な責務:

- `/api/config` を提供する．
- project `config/*-*.*` content を list/load する．
- 許可された config file を serve する．
- generated plot content などの transient content を管理する．

`/api/config/contentlist` と `/api/config/content/{filename}` は，UI component が dashboard，plot，cruise，その他 user content を発見するために使われます．

## `DataSourceComponent` and `DataSource`

`DataSourceComponent` は data source 用の plugin-backed component です．

各 `DataSource` plugin は次の route を提供します．

```text
GET /api/channels
GET /api/data/{channels}
GET /api/blob/{channel}
startup
shutdown
```

Base `DataSource` class は sync/async のどちらの plugin 実装にも対応します．

```text
initialize()       -> aio_initialize()
finalize()         -> aio_finalize()
get_channels()     -> aio_get_channels()
get_timeseries()   -> aio_get_timeseries()
get_object()       -> aio_get_object()
get_blob()         -> aio_get_blob()
```

Data query flow:

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

`DataSource.resample()` helper は time-series data を bucket に揃え，`last`，`mean`，`median`，`min`，`max`，`count`，`sem` などの reducer を support します．

## `ExportComponent`

`ExportComponent` は project config から export plugin を読み込みます．

また default export support を必ず追加します．

- CSV export が設定されていなければ CSV export．
- Notebook/Jupyter export が設定されていなければ Notebook export．

実際の export route は export plugin 側が提供します．

## `UserModuleComponent`

`sd_usermodule.py` は SlowDash の in-process Python extension mechanism を提供します．

User module は project configuration から読み込まれ，`UserModuleThread` 内で実行されます．Module は lifecycle callback を定義できます．

```text
_setup(app, params) or _setup(app) or _setup()
_initialize(params) or _initialize()
_run()
_loop()
_finalize()
```

User module は，定義されている関数に応じて，API handler，content，HTML，layout，channel/data hook，control command も提供できます．

User-module thread は通常，自分自身の event loop を使います．`_run()` と `_loop()` が async-compatible な場合のみ，設定により main event loop を使えます．

## `TaskModuleComponent`

`sd_taskmodule.py` は現行の in-process task module system です．

User-module mechanism を拡張し，task command parsing，command execution，`ControlSystem` integration を追加します．

主な route:

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

Export された control node は current channel として公開され，`/api/data/{channels}` から読めます．Incoming current-data message は `/api/consume/current_data` を通して exported variable の設定にも使われます．

## `UserHtmlComponent`

`sd_userhtml.py` は user-provided HTML と関連 content を配信します．また user URL を internal config/content API に redirect または map します．

これにより，project-specific UI page を core server を変更せず project configuration/content area に置けます．

## `MeshComponent`

`sd_mesh.py` は `/api/consume/current_data` で受け取った current data の cache を保持します．

主な役割:

- selected topic への websocket attachment．
- `/api/emit/{topic}` の re-emission と websocket forwarding．
- current-data caching．
- cache-backed current channel による `/api/channels` augmentation．
- latest cache value による `/api/data/{channels}` augmentation．

この component は data source より前に include されます．そのため custom response が data-source response と cache data を merge できます．

## `SlowMQComponent`

`sd_slowmq.py` は組み込み websocket pub/sub service を提供します．

主な route:

```text
WEBSOCKET /ws/slowmq
```

各 connected client は次を持ちます．

- client id．
- optional name．
- websocket．
- 0 個以上の topic-pattern subscription．

Message は headers を含みます．Header の `action` により，その message が publish，subscribe，unsubscribe のどれかが決まります．

Topic pattern は dot-separated で，次を support します．

- `*`: ちょうど 1 token に match．
- `>`: trailing token 0 個以上に match．ただし final token としてのみ使用可能．

## Other components

その他の server component:

- `ConsoleComponent`: display/API 用に console output を capture する．
- `MiscApiComponent`: miscellaneous utility API．
- `BlobStorage_File`: data source で使われる file-backed blob storage．

# Plugin Architecture

Plugin は `app/plugin` 以下の通常の Python module です．Filename と class name により動的に読み込まれます．

Data source の例:

```yaml
slowdash_project:
  data_source:
    type: SQLite
    parameters:
      ...
```

これは次に解決されます．

```text
datasource_SQLite.py
DataSource_SQLite
```

Export の例:

```yaml
slowdash_project:
  export:
    type: CSV
```

これは次に解決されます．

```text
export_CSV.py
Export_CSV
```

`PluginComponent` は default で nested `parameters` dictionary を root parameter dictionary に merge します．これにより plugin constructor は flatten された parameter view を使えます．

# Data Query Communication Flow

最も一般的な read path:

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

`/api/data/{channels}` では，`DataSource` plugin が SlowDash data model 形式の data を返します．Cache component は次の場合に current value を追加できます．

- requested channel が cache-backed である．
- cached timestamp が requested time window に入っている．
- existing response が存在しない，または cached value より古い．

# Write, Emit, and Current-Data Flow

Current-data update は次の経路で SlowDash に入れられます．

```text
POST /api/emit/{topic}
POST /api/consume/current_data
internal app.request_emit(topic, message, sender=...)
```

典型的な flow:

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

`sender` parameter は，task 自身が publish した値を同じ task variable path に反射させないために使われます．

# Control Flow

Control command は `/api/control` を使います．

現行 in-process task flow:

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

User module も，定義した hook に応じて command processing に参加できます．

# SlowPy Library Role

SlowPy は server-side component と user code の両方から使われます．

## Data object model

SlowPy は SlowDash-compatible data に変換できる Python object を提供します．

- scalar value．
- `TimeSeries`．
- histogram．
- graph．
- trend．
- tree．
- table．
- `slowdashify` による matplotlib-derived data．

これらの object は task/user code，storage writer，current data を publish する API で使われます．

## Control nodes

`slowpy/control/node.py` の `ControlNode` は readable/writable control endpoint の base abstraction です．

主な method:

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

Async method は default では sync method に delegate します．`_is_thread_safe` が設定されている場合，sync `get()` と `set()` call は `asyncio.to_thread()` 経由で実行できます．

`slowpy/control/control_*.py` 以下の control module は，device，network，message，shell，HTTP，datastore，protocol integration の concrete implementation を提供します．

## Data stores

SlowPy data store は write-side storage helper を提供します．

`store/factory.py` は URL を implementation に map します．

```text
postgresql:// -> DataStore_PostgreSQL
mysql://      -> DataStore_MySQL
sqlite://     -> DataStore_SQLite
influxdb2://  -> DataStore_InfluxDB2
redis://      -> DataStore_Redis
csv:///       -> DataStore_CSV
dump:///      -> DataStore_TextDump
```

`DataStore` は次を support します．

```text
append(values, tag=None, timestamp=None)
update(values, tag=None, timestamp=None)
close()
```

Value には scalar，field dictionary，data element，`TimeSeries` を使えます．

# SlowDash にとって重要な Slowlette 内部仕様

SlowDash のいくつかの挙動は，Slowlette の設計に直接依存しています．

### Multiple handlers can answer the same route

Slowlette は app tree 内のすべての matching handler を呼びます．そのため，複数 component が `/api/config`，`/api/channels`，`/api/data/{channels}` を提供できます．

### Response merging is part of the application model

Merged response は単なる便利機能ではありません．独立に開発された component や plugin から aggregate API response を組み立てるための仕組みです．

### Component order is meaningful

Custom response は後続 component の response を merge できるため，`slowdash.py` の include order は runtime behavior の一部です．

### Internal API calls use the same router

`App.request()`，`request_config()`，`request_channels()`，`request_data()`，`request_emit()` は `self.slowlette(...)` を直接呼びます．そのため server-side の producer/consumer も，外部 HTTP client と同じ routing / response merging model を使います．

# Main Flow Summary

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

# Development Notes

- 新しい API component を追加する場合は，`Component` を subclass し，`slowdash.py` から include する．
- 新しい data source を追加する場合は，新しい `app/plugin/datasource_*.py` file で `DataSource` を subclass する．
- 新しい exporter を追加する場合は，`export_*.py` plugin を追加する．
- 他 component と aggregate する endpoint では，dict/list content を返して response merging を利用する．
- 後続 component の output を加工する endpoint では，custom `slowlette.Response` subclass を返し，`merge_response()` を override する．
- `public_config()` には secret を入れない．`/api/config` は client に公開される．
- Component include order の変更には注意する．merge behavior が変わる可能性がある．
- Server-side code が外部 API client と同じ route logic を使うべき場合は，internal `App.request*()` helper を使う．

