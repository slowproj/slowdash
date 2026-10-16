---
title: ソース構造 - Python バックエンド
---

# 全体構造

SlowDash は，主に 4 つの Python レイヤーで構成されています．

```text
Client / CLI / CGI
    |
    v
Slowlette
    - ASGI/WSGI アダプタ
    - URL ルーティング
    - リクエスト引数のバインディング
    - レスポンスのマージ
    |
    v
SlowDash サーバーコンポーネント
    - プロジェクト/設定の処理
    - データソース API
    - ユーザーモジュール API と Mesh タスクのプロキシ
    - エクスポート API
    - ユーザー HTML/コンテンツ API
    - SlowMQ，WebMesh（SSE），Mesh レジストリ
    |
    v
プラグインとライブラリ
    - app/plugin のデータソースとエクスポータ
    - slowpy のデータオブジェクト，制御ノード，ストア，クライアントヘルパー
    - slowpy.mesh の pub/sub，RPC，Tasklet ランタイム
```

中心となるサーバーオブジェクトは，`app/server/slowdash.py` の `App` です．`App` は `slowlette.App` を継承し，`Project` を生成して実行環境を整えたうえで，SlowDash の各コンポーネントを Slowlette のルーターに組み込みます．

タスクは `slowdash-task` などの別プロセスで動作し，`slowpy.mesh` を通じてサーバーと通信します．`UserModuleComponent` によるプロセス内ユーザーモジュールの仕組みは引き続き存在します．

# 主要ディレクトリ

### `app/server`

このディレクトリには，SlowDash のウェブアプリケーションと組み込みの API コンポーネントが含まれます．

主なファイル:

- `slowdash.py`: アプリケーションのエントリーポイント，コマンドラインのエントリーポイント，コンポーネントの組み立て，内部 API のヘルパー．
- `slowdash_wsgi.py` と `slowdash.cgi`: WSGI/CGI のエントリーポイント．
- `sd_project.py`: プロジェクトの探索，YAML の読み込み，環境変数やコマンドの置換，公開用のプロジェクトメタデータ．
- `sd_component.py`: コンポーネントおよびプラグインベースのコンポーネントの基底クラス．
- `sd_config.py`: `/api/config`，設定ファイル/コンテンツ API，一時コンテンツのサポート．
- `sd_datasource.py`: データソースプラグインの基底クラスと，`/api/channels`，`/api/data`，`/api/blob` の各ルート．
- `sd_datasource_SQL.py`，`sd_datasource_TableStore.py`，`sd_dataschema.py`: データソース共通のヘルパー．
- `sd_blobstorage.py`: blob ストレージのヘルパー．
- `sd_export.py`: エクスポートプラグインのコンポーネント．
- `sd_usermodule.py`: プロセス内で動作するユーザーモジュールの拡張機構．
- `sd_task.py`: タスクカタログ，プロセス制御，Mesh 上のタスク探索，RPC・変数・コンテンツのプロキシ．
- `slowdash-task.py`: タスクスクリプトを読み込み，別プロセスで `Tasklet` を実行する CLI．
- `sd_userhtml.py`: ユーザー提供の HTML/コンテンツの配信．
- `sd_console.py`: 従来のコンソールキャプチャ実装（現在の `App` には組み込まれない）．
- `sd_misc_api.py`: その他の組み込み API エンドポイント．
- `sd_webmesh.py`: Mesh トピックとブラウザの SSE 接続の橋渡し，配信データのキャッシュ．
- `sd_mesh_registry.py`: Mesh の共有レジストリ，pub/sub の最新値キャッシュ，ログの収集．
- `sd_slowmq.py`: 組み込みの websocket ベースの pub/sub コンポーネント．
- `sd_version.py`: バージョン文字列．

### `app/plugin`

このディレクトリには，`PluginComponent` によって読み込まれるプラグインモジュールが含まれます．

データソースプラグイン:

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

エクスポートプラグイン:

- `export_CSV.py`
- `export_Notebook.py`
- `export_Jupyter.py`

プラグインのファイル名とクラス名は命名規約で決まります．たとえばデータソースの種別が `SQLite` の場合は，次のように対応します．

```text
app/plugin/datasource_SQLite.py
DataSource_SQLite
```

### `lib/slowlette`

Slowlette は，SlowDash が使用する小さなウェブフレームワークです．

主なファイル:

- `app.py`: `App` と `Slowlette` のアプリケーションクラス．
- `router.py`: デコレータ，パスのマッチング，引数のバインディング，サブアプリへのディスパッチ，レスポンスのマージ．
- `server.py`: ASGI/WSGI のディスパッチと，開発用サーバーのヘルパー．
- `request.py`: 解析済みの HTTP リクエストオブジェクト．
- `response.py`: レスポンスオブジェクト，コンテンツのマージ，ファイルレスポンス．
- `model.py`: JSON リクエストボディのラッパー．
- `websocket.py`: websocket のラッパーと，接続のクローズ処理．
- `eventstream.py`: WebMesh が使う Server-Sent Events（SSE）のラッパーと切断処理．
- `middleware.py`: ミドルウェアのサポート．

### `lib/slowpy`

SlowPy は，データ型，制御の抽象化，ストレージへの書き込み機能，クライアントヘルパー，作図ヘルパー，Mesh 通信とタスク実行を提供します．

主な領域:

- トップレベルのデータオブジェクト:
  - `basetypes.py`
  - `histograms.py`
  - `graphs.py`
  - `trend.py`
  - `treetable.py`
  - `mpldata.py`
  - `slowplot.py`
- 制御システム:
  - `control/node.py`
  - `control/system.py`
  - `control/control_*.py`
- データストア:
  - `store/store.py`
  - `store/factory.py`
  - `store/store_SQL.py`
  - `store/store_CSV.py`
  - `store/store_HDF5.py`
  - `store/store_InfluxDB2.py`
  - `store/store_Redis.py`
- クライアントヘルパー:
  - `slowfetch.py`

公開されているトップレベルの `slowpy` パッケージは，`Histogram`，`Graph`，`Trend`，`Tree`，`Table`，`TimeSeries`，`SlowFetch`，`slowdashify`，`slowplot` など，よく使われるデータオブジェクトやヘルパーをエクスポートします．

### `lib/slowpy/slowpy/mesh`

サーバーと独立したタスクの両方が利用する通信・実行ライブラリです．

- `__init__.py`: `Mesh`，`Tasklet`，`RetainerAutocide`，`MeshStdio`，`MeshLogHandler`，`DataPacket`，`FormPacket` を公開する．
- `mesh.py`: pub/sub トランスポートの選択，トピック変換，RPC，関数・制御ノードのエクスポート，リモートノードとレジストリのクライアント．
- `tasklet.py`: コールバック実行，タスク仕様の通知，ハートビート，終了処理，親プロセス消失時の終了補助．
- `packet.py`: データおよびフォーム更新のトピック・ヘッダ・ボディへの変換．
- `stdio.py`: 標準入出力を Mesh に接続する，スレッドを考慮したルーターとキュー．
- `logger.py`: Python のログレコードを Mesh に配信するハンドラ．
- `dash.py`: `Tasklet.dash` が利用する非同期 HTTP クライアント（設定，チャンネル，データの取得）．

# アプリケーションの起動フロー

## コマンドラインまたはサーバーの起動

主要なエントリーポイントは `app/server/slowdash.py` です．

通常の起動シーケンスは次のとおりです．

1. コマンドラインオプションを解析する．
2. `App(project_dir=..., project_file=..., port=..., is_cgi=..., is_command=..., is_async=...)` を生成する．
3. `App` が `Project` を生成する．
4. `Project` が SlowDash のシステムディレクトリとプロジェクトディレクトリを探す．
5. `Project` が `SlowdashProject.yaml` を読み込む．設定によっては，環境変数から初期設定を生成する．
6. プロジェクトディレクトリが存在する場合，`App` はプロセスの作業ディレクトリをプロジェクトディレクトリに移す．
7. `App` は，システムのプラグインディレクトリ，プロジェクトディレクトリ，プロジェクトの `config` ディレクトリを `sys.path` に追加する．
8. `App` がすべての組み込みコンポーネントを，自身の Slowlette ルーターに組み込む．
9. 選択されたモードに応じて，ASGI，WSGI，CGI，またはコマンドラインの内部リクエストとして実行される．

## コンポーネントの組み込み順序

`slowdash.py` は，コンポーネントを次の順序で組み込みます．

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

Slowlette は複数のハンドラの応答を後ろから前へマージするため，この順序には意味があります．

- `WebMeshComponent` は `DataSourceComponent` より前にあり，他の応答に含まれないチャンネルをキャッシュから補います．
- `UserModuleComponent` はデータソースより前ですが，`TaskComponent` は最後です．従来のプロセス内タスクを前提にした順序ではありません．
- `ConsoleComponent` は組み込まれません．タスクの標準入出力とログには `MeshStdio` と `MeshLogHandler` を使います．

`MeshRegistryComponent`，`WebMeshComponent`，`TaskComponent` は `post_startup` で Mesh に接続します．ASGI の `post_startup` は `lifespan.startup.complete` の送信後に呼ばれるため，内蔵 SlowMQ の WebSocket を受け付けられる段階で接続できます．Mesh を利用する構成では，有効な `project.mesh_url` と稼働中のトランスポートが必要です．WebMesh の起動は `app.is_async` によって制御されます．

# Slowlette のルーティングとレスポンスモデル

## リクエストの流れ

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
                (eventstream routes send SSE through EventStream)
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

Slowlette は，受信した URL を `Request` に変換します．

- `Request.path`: デコード済みのパス要素．
- `Request.query`: デコード済みのクエリ辞書．
- `Request.headers`: サーバー層から渡される，正規化されたヘッダ辞書．
- `Request.body`: 生のボディ，または内部ディスパッチ用の Python オブジェクト．

## デコレータと引数のバインディング

ハンドラは，次のようなデコレータで宣言します．

```python
@slowlette.get('/api/channels')
@slowlette.post('/api/control')
@slowlette.websocket('/ws/slowmq')
@slowlette.eventstream('/event/webmesh/attach')
@slowlette.on_event('startup')
```

`router.py` の `PathRule` は，デコレートされた関数のシグネチャを調べ，次のものをバインドします．

- `{channels}` のようなパスパラメータ．
- 名前で一致するクエリパラメータ．
- `bytes` のリクエストボディ．
- JSON ボディのラッパー．
- リクエスト全体を表す `Request`．
- `WebSocket` と `EventStream`．
- パスのリスト，またはクエリの辞書．

ルーターはサブアプリを組み込めます．各コンポーネント自体が `slowlette.App` であるため，コンポーネントごとに独自のルートを追加できます．

## レスポンスのマージ

Slowlette のディスパッチは，最初に一致したハンドラで止まりません．コンポーネントツリーをたどってすべての一致するレスポンスを集め，下から上へとマージします．

`Response.merge_response()` のデフォルトのマージ動作は次のとおりです．

- ステータスコードが大きいレスポンスが優先される．
- ステータスコードが同じ場合は，コンテンツをマージする．
- 辞書のコンテンツはディープマージされる．
- リストのコンテンツは末尾に追加される．
- 文字列のコンテンツは改行を挟んで連結される．

SlowDash は，集約型のエンドポイントのためにこの仕組みを利用しています．

- `/api/config` は，複数のコンポーネントの `public_config()` の応答から組み立てられる．
- `/api/channels` は，複数のソースからのチャンネルを統合できる．
- `/api/data/{channels}` は，データソースの結果と現在値データのキャッシュをマージできる．

一部のコンポーネントは，`merge_response()` をオーバーライドした独自の `Response` サブクラスを返します．たとえば現在値データのキャッシュコンポーネントは，データソースの応答が生成された後に現在値を追加します．

# プロジェクト設定のフロー

`sd_project.py` の `Project` は，プロジェクト設定の探索と読み込みを担当します．

設定の取得元は次のとおりです．

1. 明示的に指定された `--project-dir` または `--project-file`．
2. `SLOWDASH_PROJECT`．
3. 親ディレクトリをたどっての `SlowdashProject.yaml` の探索．
4. `SLOWDASH_INIT_DATASOURCE_URL` による，環境変数ベースの初期データソース．

プロジェクトファイルは `slowdash_project` 辞書を含む必要があります．読み込み時には，`Substitution` が次の形式を含む文字列の置換を処理します．

```text
${VARIABLE}
${VARIABLE-default}
${VARIABLE:-default-like-empty-is-null}
$(COMMAND)
$$
```

読み込み後の処理は次のとおりです．

- `name` と `title` が無ければ補完される．
- `system` のデフォルトは `{}` になる．
- `authentication.key` は `project.auth_list` になる．
- `system.our_security_is_perfect` が `project.is_secure` を制御する．

`ConfigComponent` は，公開用のプロジェクトメタデータを `/api/config` から提供します．ただし，生のプロジェクト設定は秘密情報を含む可能性があるため，そのまま公開しません．

`project.mesh_url` は `slowdash_project.mesh.url` から取得します．未指定でサーバーポートがある場合は，`slowmq://{hostname}:{port}` を使います．`Mesh.connect()` は SlowMQ に加えて NATS，MQTT，Redis，RabbitMQ のトランスポートを選択できます．URL を与えない `Mesh` はローカルの pub/sub を使います．

# 組み込みサーバーコンポーネント

## `Component` と `PluginComponent`

`Component` は，サーバーコンポーネントの基底クラスです．次のものを提供します．

- `self.app`
- `self.project`
- `public_config()` を返すデフォルトの `/api/config` ルート

`PluginComponent` は，プロジェクト設定からコンポーネントのプラグインを構築します．

1. `project.config[component_type]`，またはその複数形を読み込む．
2. 単一のノードをリストに正規化する．
3. プラグインのファイル名とクラス名を解決する．
4. `app/plugin` からプラグインモジュールを読み込む．
5. プラグインクラスをインスタンス化する．
6. 各プラグインを Slowlette のサブアプリとして組み込む．

アプリが非同期でない場合は，利用可能であれば `_NoAsync` 版のプラグインファイルが優先されます．

## `ConfigComponent`

主な責務は次のとおりです．

- `/api/config` を提供する．
- プロジェクトの `config/*-*.*` コンテンツを一覧・読み込みする．
- 許可されている場合に設定ファイルを配信する．
- 生成されたプロット内容などの一時コンテンツを管理する．

`/api/config/contentlist` と `/api/config/content/{filename}` のエンドポイントは，UI コンポーネントがダッシュボード，プロット，cruise，その他のユーザーコンテンツを見つけるために使われます．

## `DataSourceComponent` と `DataSource`

`DataSourceComponent` は，データソース用のプラグインベースのコンポーネントです．

各 `DataSource` プラグインは，次のルートを提供します．

```text
GET /api/channels
GET /api/data/{channels}
GET /api/blob/{channel}
startup
shutdown
```

基底の `DataSource` クラスは，同期・非同期のどちらのプラグイン実装にも対応します．

```text
initialize()       -> aio_initialize()
finalize()         -> aio_finalize()
get_channels()     -> aio_get_channels()
get_timeseries()   -> aio_get_timeseries()
get_object()       -> aio_get_object()
get_blob()         -> aio_get_blob()
```

データ取得の流れは次のとおりです．

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

`DataSource.resample()` ヘルパーは，時系列データをビンに揃え，`last`，`mean`，`median`，`min`，`max`，`count`，`sem` などのリデューサに対応します．

## `ExportComponent`

`ExportComponent` は，プロジェクト設定からエクスポートプラグインを読み込みます．

また，次のデフォルトのエクスポート機能を必ず追加します．

- CSV エクスポートが設定されていなければ，CSV エクスポート．
- Notebook と Jupyter のいずれのエクスポートも設定されていなければ，Notebook エクスポート．

実際のエクスポート用ルートは，エクスポートプラグイン側が提供します．

## `UserModuleComponent`

`sd_usermodule.py` は，SlowDash のプロセス内 Python 拡張機構を提供します．

ユーザーモジュールはプロジェクト設定から読み込まれ，`UserModuleThread` 内で実行されます．モジュールは，次のライフサイクルコールバックを定義できます．

```text
_setup(app, params) or _setup(app) or _setup()
_initialize(params) or _initialize()
_run()
_loop()
_finalize()
```

ユーザーモジュールは，定義されている関数に応じて，API ハンドラ，コンテンツ，HTML，レイアウト，チャンネル/データのフック，制御コマンドも提供できます．

ユーザーモジュールのスレッドは，通常は自身のイベントループを使います．`_run()` と `_loop()` が非同期に対応している場合に限り，設定によってメインのイベントループを使えます．

## `TaskComponent`

`sd_task.py` は，Mesh 上のタスクを HTTP API に公開するプロキシと，ローカルタスクのプロセスマネージャです．削除された `sd_taskmodule.py` のプロセス内スレッド実行を引き継ぐ実装ではありません．

主なルート:

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

- `task` / `tasks` 設定と `config/slowtask-*.py` からカタログを作る．設定の既定コマンドは `slowdash-task <file_path> --name=<name>` で，Mesh URL と JSON パラメータも渡される．`auto_start`（互換名 `auto_load`）に従って `subprocess.Popen` で起動する．
- `sd.task.spec.>`，`sd.task.exit.>`，`sd.task.heartbeat.>`，`sd.task.life_event.>` を購読し，`mesh_id` ごとの `TaskProxy` を管理する．`sd.task.control.introduce` でタスク仕様の再通知を要求するため，別途起動されたタスクも登録できる．
- `TaskFunctionProxy` は通知された引数仕様に基づき RPC 引数を整える．`TaskVariableProxy` は `mesh.remote_node('<task>.<variable>')` を使って値を読む．
- タスク制御の `action` は `start`，`stop`，`kill`，`purge`．`stop` は `<task>._sd_stop` RPC，`kill` はこのサーバーが保持する子プロセス，`purge` は終了通知による登録解除を扱う．
- エクスポートされた制御ノードはチャンネルとなり，現在時刻を含むデータ要求でリモートから読まれる．タスクのコンテンツは `<task>._sd_get_content` RPC を通じて設定/コンテンツ API に公開される．

`slowdash-task.py` はスクリプト内の `Tasklet` を探して実行します．見つからなければ `Tasklet(use_oldstyle_callbacks=True)` を作り，従来のコールバックを読み込みます．スクリプト読み込み時から標準入出力とログを Mesh に接続し，`RetainerAutocide` により親プロセス消失時の終了も扱います．

### タスクの識別とライフサイクル

タスク名（例: `sensor`）は RPC の名前空間で，`mesh_id` は接続する Mesh インスタンスの識別子です．`Mesh.connect()` は名前，ホスト名，PID，プロセス内の連番から `mesh_id` を作ります．タスク表は `mesh_id` で管理されますが，RPC 要求の配送先は `sd.rpc.<taskname>` なので，同じ名前の複数タスクが要求を受け取ることがあります．通常のタスク制御では一意の名前を使います．

カタログは「起動可能なスクリプト」，タスク表は「仕様を通知したタスク」，プロセス表は「このサーバーが起動した子プロセス」を表します．外部で起動したタスクは Mesh に登録できますが，その PID をサーバーが所有するわけではありません．`kill` は追跡中の子プロセスだけが対象で，`purge` は登録を外す操作です．再起動操作は現在の API では stop/start の組み合わせになります．

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

ハートビートは `Tasklet` のメインループから既定で約 5 秒ごとに送られます．サーバーはチャンネル取得やタスク操作などで `_check_task_heartbeats()` を呼び，通知された期限に約 5 秒の猶予を加えて生存状態を判断します．独立した常時監視スレッドによる判定ではありません．ハートビート欠落はプロセス終了の確定情報ではなく，タスクのイベントループがブロックしている場合にも起こります．

### タスク構成の最小例

次の例では，SlowDash がポート 18881 で動作し，内蔵 SlowMQ が使えることを前提とします．設定中の Mesh URL は稼働中のブローカーを指します．

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

`config/slowtask-sensor.py` の内容:

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

`slowdash-task` が読み込むときは，既存の `task` を検出して `run_module()` を呼びます．直接 Python で実行するときは `__main__` の `task.run()` が使われます．この例は `temperature` チャンネルを配信し，`sensor.set_temperature` を RPC として公開します．制御ノードのエクスポートとは別に，関数を公開している点に注意してください．

```text
POST /api/control
Content-Type: application/json

{"sensor.set_temperature()": null, "value": 20.0}
```

コマンド名は JSON のキーで指定し，残りのフィールドを引数にします．タスク仕様への掲載には，引数を `int`，`float`，`str`，`bool` で注釈するか，これらの型を推定できる既定値を使います．実装は仕様の作成とサーバー側の型変換にこれらの情報を利用します．

## `UserHtmlComponent`

`sd_userhtml.py` は，ユーザー提供の HTML と関連コンテンツを配信します．また，ユーザー URL を内部の設定/コンテンツ API へリダイレクトまたはマッピングします．

これにより，プロジェクト固有の UI ページを，コアサーバーを変更することなく，プロジェクトの設定/コンテンツ領域に置けます．

## `WebMeshComponent`

`sd_webmesh.py` は Mesh とブラウザの橋渡しを行います．削除された `sd_mesh.py` の現在値キャッシュに相当する処理は，このファイルの `DataCache` とマージ用レスポンスに移っています．ブラウザへの配信には SSE を使います．

```text
SSE  /event/webmesh/attach
POST /api/webmesh/subscribe
POST /api/webmesh/unsubscribe
POST /api/webmesh/publish/{topic}
GET  /api/channels
GET  /api/data/{*}
```

`data.>`，`form.>`，タスクの life-event/heartbeat/stdout，`log.>` を購読します．データをキャッシュし，ブラウザの購読に一致するメッセージをクライアントごとのキューへ送ります．SSE の `register` イベントは `client_id` を返し，`message` イベントは `subscribed_topic`，`headers`，`body` を含みます．キューの上限は 10 件で，満杯になったクライアントは切断されます．

ブラウザは `data.*.<channel>`，`form.<form>.>` のようなフォーム用トピック，およびコード内の固定トピックリストを使って購読します．現在の振り分けは完全な汎用ワイルドカードマッチングではなく，`_subscribe_mesh()` のトピック正規化に基づきます．`unsubscribe` は指定クライアントの全購読を解除します．

`ChannelMergerResponse` は，配信されたチャンネルを `streaming: True` として不足分だけ追加します．`DataMergerResponse` は，他の応答にチャンネルが存在せず，キャッシュの `t` が単一の数値で要求時間範囲に入る場合だけデータを補います．既存チャンネルの値は上書きせず，時系列配列も結合しません．

### ブラウザ接続の手順

1. `EventSource` で `/event/webmesh/attach` を開く．
2. `register` イベントの JSON から `client_id` を取得する．
3. `/api/webmesh/subscribe` に `{"client_id":"...","topic":"data.*.temperature"}` を JSON として POST する．`client_id` はこのルートではボディに含める．
4. `message` イベントの JSON を読み，`body` のチャンネルデータを表示する．`headers.topic` は元のトピック，`subscribed_topic` はブラウザの購読用に正規化されたトピックである．
5. 全購読を解除する場合は `/api/webmesh/unsubscribe?client_id=...` に POST する．SSE が切断された場合も，その接続のキューと購読は削除される．

`app/site/slowjs/control.mjs` のクライアントは，通常のチャンネルを `data.*.<channel>` に変換し，`@mesh:` で始まる指定はプレフィックスを除いたトピックとして扱います．エラー時には接続を作り直し，新しい `client_id` の登録後に購読を再送します．

SSE 接続や subscribe 自体はキャッシュ済みの値を再送しません．初期表示には `/api/data` やレジストリの取得を併用します．また WebMesh の受信キューはライブ配信用であり，切断中のメッセージを永続保存して再生するものではありません．

## `SlowMQComponent`

`sd_slowmq.py` は，組み込みの websocket pub/sub サービスを提供します．

主なルートは次のとおりです．

```text
WEBSOCKET /ws/slowmq
```

接続中の各クライアントは，次のものを持ちます．

- クライアント ID．
- 省略可能な名前．
- websocket．
- 0 個以上のトピックパターンのサブスクリプション．

メッセージはヘッダを含みます．ヘッダの `action` によって，そのメッセージが publish，subscribe，unsubscribe のいずれの操作かが決まります．

トピックパターンはドット区切りで，次のものに対応します．

- `*`: ちょうど 1 トークンに一致する．
- `>`: 末尾の 0 個以上のトークンに一致する．ただし最後のトークンとしてのみ使用できる．

SlowMQ は Mesh のトランスポートとして使う WebSocket ブローカーであり，ブラウザ向け SSE の WebMesh とは役割が異なります．`AsyncSlowMQ` 制御ノードがこのサービスに接続します．subscribe 要求には `message_id` に対応した `reply_to` の確認応答を返します．切断時には購読を削除し，送信が 5 回連続で失敗したクライアントも除去します．統計と購読数は `/api/config` の `slowmq` に公開されます．

### メッセージ形式と配送

SlowMQ の WebSocket では JSON の `headers` と `data` を使います．Mesh の購読コールバックはこれを `(headers, body)` として受け取り，WebMesh の SSE は `body` というフィールド名でブラウザに渡します．同じメッセージでも境界ごとにボディの名前が異なります．スカラー値を配信した例は次のとおりです（時刻は例示）．

```json
{
  "headers": {"topic": "data.stream.temperature"},
  "data": {"temperature": {"t": 1780000000.0, "x": 12.3}}
}
```

`action` を省略すると publish と解釈されます．`DataPacket` の `tag='temperature'` はトピックの末尾とボディのチャンネル名に使われます．`t` は `start` を省略した場合は UNIX 時刻で，`start` があればその時刻からの相対秒です．時系列では `t` が配列となり，WebMesh の HTTP キャッシュ補完の対象外になります．

`AsyncSlowMQNode` は送信用の WebSocket を共有し，購読はトピックフィルタごとに WebSocket を持ちます．SlowMQ ブローカーは現在接続中の購読者へメッセージを転送します．ブローカー自身には履歴の永続化や publish 完了に対するアプリケーションの処理済み確認はありません．subscribe の確認応答と RPC の返信は別の仕組みです．

## `MeshRegistryComponent`

`sd_mesh_registry.py` の `Registry` は，ドット区切りのキーに値，revision，更新時刻を保存します．`MeshRegistryComponent` はこれを Mesh 名 `sd_mesh_registry` の `set`，`get`，`keys`，`delete` RPC として公開します．クライアントは `mesh.registry.aio_set()` / `aio_get()` / `aio_keys()` / `aio_delete()` を使います．

```text
GET /api/registry/keys/{path}
GET /api/registry/value/{key}
GET /api/data/{*}                 # @registry:<key> channels
GET /api/log
```

- 末尾が `>` のキーはサブツリーを指定する．`with_meta` でメタデータを取得でき，単一キーの更新・削除には `cas_revision` を使える．サブツリーの設定には CAS は実装されていない．
- `server.url` に SlowDash の URL を登録する．`Tasklet` はこれを HTTP ヘルパーの接続先探索に利用する．
- `>` を購読し，`sd.rpc` で始まるトピックを除く最新のメッセージボディを `pubsub.<topic>` に保存する．これは WebMesh のチャンネル用キャッシュとは別のレジストリである．
- `pubsub.form.` と，作業ディレクトリ内の `registry-*.json` から読み込んだ領域を永続化対象とし，値の設定時に保存する．すべてのキーを永続化する仕組みではない．
- `log.>` のログをメモリに保持し，`/api/log` で表形式として返す．`@registry:` で始まるデータチャンネルは，レジストリ値を `/api/data` の形式で読むための経路となる．

### 状態の保存先の使い分け

| 保存先 | 内容 | 読み取り経路 | 寿命 |
|---|---|---|---|
| WebMesh `DataCache` | 配信チャンネルの最新レコードと型 | `/api/channels`，`/api/data` の補完 | サーバープロセス内 |
| Mesh `Registry` | 共有キーと最新の pub/sub ボディ | レジストリ RPC，`/api/registry/*`，`@registry:` | 主にメモリ，指定領域のみ JSON 保存 |
| Task のエクスポート済みノード | タスクが管理する現在値 | ノード RPC，`TaskComponent` のデータ API | タスク/デバイス側に依存 |
| `slowpy.store` / データソース | 保存済み時系列やオブジェクト | データソースの `/api/data` | 使用するストレージに依存 |

配信したデータを履歴として保存したい場合は，タスクや購読側で明示的に `DataStore.append()` などを呼びます．Mesh に配信するだけでデータベースへ保存されるわけではありません．

レジストリの読み方の例:

- `mesh.registry.aio_get('pubsub.form.settings.>')`: settings フォームの最新メッセージをサブツリーとして取得する．
- `mesh.registry.aio_get('state.run', with_meta=True)`: `key`，`value`，`revision`，`updated` を取得する．
- `mesh.registry.aio_set('state.run', 'running', cas_revision=revision)`: 読み取った revision がまだ一致する場合だけ更新し，不一致なら `None` を返す．

いずれも非同期呼び出しなので `await` を使います．revision は現在のレジストリ内での競合検出用であり，JSON 保存からの復元時にはメタデータが引き継がれません．また現行の `delete()` はメモリ上の削除で，永続ファイルの書き直しを行いません．

## その他のコンポーネント

その他のサーバーコンポーネントは次のとおりです．

- `ConsoleComponent`: 従来のコンソールキャプチャ実装で，現在の `App` には組み込まれない．
- `MiscApiComponent`: その他のユーティリティ API．
- `BlobStorage_File`: データソースが使う，ファイルベースの blob ストレージ．

# プラグインアーキテクチャ

プラグインは，`app/plugin` 以下にある通常の Python モジュールです．ファイル名とクラス名によって動的に読み込まれます．

データソースの例:

```yaml
slowdash_project:
  data_source:
    type: SQLite
    parameters:
      ...
```

これは次のように解決されます．

```text
datasource_SQLite.py
DataSource_SQLite
```

エクスポートの例:

```yaml
slowdash_project:
  export:
    type: CSV
```

これは次のように解決されます．

```text
export_CSV.py
Export_CSV
```

また `PluginComponent` は，デフォルトでネストした `parameters` 辞書をルートのパラメータ辞書にマージします．これにより，プラグインのコンストラクタは平坦化されたパラメータを参照できます．

# データ取得の通信フロー

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

`/api/data` の結果には，保存済みデータ，タスクのリモートノードの現在値，WebMesh の配信キャッシュ，レジストリ値が参加できます．`TaskComponent` と `WebMeshComponent` は，チャンネル名に `/` を含められるよう `/api/data/{*}` を使います．

WebMesh のキャッシュ補完は，欠けているチャンネルの単一時刻データだけを対象にします．一方，`TaskComponent.DataMergerResponse` には，より新しい現在値を単一値や時系列の末尾へ追加する処理があります．この 2 つのマージ処理は同じではなく，最終的な応答はコンポーネントの組み込み順序にも依存します．

# 配信・現在値データのフロー

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

HTTP クライアントは `POST /api/webmesh/publish/{topic}` から JSON ボディを Mesh に配信できます．`POST /api/control` の `publish <topic>(...)` 形式も pub/sub に変換されます．フォーム更新には `FormPacket` と `form.<form>.<element>` を使い，レジストリの `pubsub.form` に最新値が保持されます．

`ControlSystem.aio_publish()` と `stream()` も，バインドされた `Tasklet` の Mesh を使って `data.stream.<name>` を送ります．配信データと，RPC で読み書きするエクスポート済み制御ノードは別の経路です．

# 制御フロー

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

`MeshRequest` はコマンド名とパラメータを解析します．旧 `await`，`reentrant`，`async`，`parallel` 接頭辞は，互換性のため警告を出して取り除かれるだけで，実行モードを選択しません．RPC の受信側ではエクスポート済み関数を呼び，戻り値がコルーチンなら await します．返信は `status`，`message`，`return_value` を持ち，相関 ID で呼び出しに対応づけられます．

制御ノードの読み書きには `mesh.remote_node('<task>.<variable>').aio_get()` / `aio_set()` を使います．内部的には `<task>._sd_node_call` RPC を通じて，エクスポートされたノードの `aio_get()` / `aio_set()` を呼びます．ユーザーモジュールは引き続き自身の制御フックで参加できます．

### RPC の返信と実行モデル

要求には `module`，`function`，`sender_id`，`reply_to`，`correlation_id`，`message_id` のヘッダと，`args` / `kwargs` のボディが含まれます．`Mesh` は相関 ID ごとの返信キューを保持し，`aio_call_many()` で必要な返信数またはタイムアウトまで待ちます．`TaskProxy` の関数呼び出しは 1 件の返信，5 秒のタイムアウトを指定します．`aio_call()` は返信の `status` を確認して `return_value` を返しますが，`aio_call_many()` は返信レコードのリストを返すため，呼び出し側が結果を確認します．

同一 Mesh インスタンスの RPC 受信ループは，関数の完了を待ってから次の要求を処理します．`async def` にしても，同じ受信ループが複数 RPC を並列実行するわけではありません．また同期関数はそのイベントループ上で直接呼ばれ，自動的にワーカースレッドへ移されません．長い処理は Tasklet のループへ分離するなど，RPC が短時間で返るように設計します．

呼び出し側のタイムアウトは，遠隔側で関数が実行されなかったことや，実行が取り消されたことを意味しません．更新操作を再試行する場合は，処理の重複を考慮する必要があります．

# SlowPy ライブラリの役割

SlowPy は，サーバー側のコンポーネントとユーザーコードの両方から使われます．

## Mesh 通信と Tasklet

`Mesh` は，`control/` の非同期 pub/sub ノードに，トピック変換，コールバック購読，RPC を重ねたものです．アプリケーションは通常 `.`，`*`，`>` のトピック表現を使い，各トランスポートに合わせて区切りとワイルドカードが変換されます．外部ブローカーを使う場合は，対応する制御モジュールの依存パッケージも必要です．

主な API:

- `aio_start()` / `aio_close()`: 接続とバックグラウンド処理の開始・終了．
- `publisher()` / `subscriber()`: 制御ノードとして pub/sub にアクセスする．
- `aio_publish()`，`aio_subscribe()`，`@mesh.on(...)`: メッセージの送受信．`publish()` は実行中のイベントループへ配信処理を登録するため，イベントループが必要．
- `@mesh.export` または `mesh.export(name, function_or_node)`: 関数・制御ノードを公開する．
- `aio_call()` は単一の RPC 戻り値，`aio_call_many()` は返信レコードのリストを返す．RPC 要求は `sd.rpc.<module>`，返信は `sd.rpc_reply.<mesh_id>` を使う．
- `remote_node()` と `registry`: リモートの制御ノードと共有レジストリへのアクセス．

`DataPacket` はスカラー，データ要素，フィールド辞書，`TimeSeries` を Mesh のボディへ変換し，`tag` がある場合はトピックにも追加します．`FormPacket` は `form.<form>.<element>` と，`form`，`element`，`value` を含むボディを生成します．

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

`Tasklet` は Mesh を所有するタスクランタイムです．`initialize()`，`finalize()`，`once()`，`loop()`，`schedule()`，`content()` のデコレータで処理を登録し，`run()` または CLI からの `run_module()` で実行します．タスク仕様には関数，引数型，制御ノード，コンテンツ，標準入出力の情報が含まれます．仕様・ハートビート・終了を `sd.task.*` に通知し，`sd.task.control.introduce` に応答します．

互換モードは `_initialize`，`_finalize`，`_run`，`_loop`，HTML/レイアウトのコールバックと公開関数を読み込みます．長い処理やループには非同期関数と非同期 I/O を使い，Mesh の受信やハートビートを止めないようにします．

`MeshStdio` は，タスクでは `sd.task.stdin.<mesh_id>` と `sd.task.stdout.<mesh_id>` に標準入出力を接続します（既定では stderr も stdout と同じトピック）．`MeshLogHandler` は Python ログを `log.>` のトピックに配信します．`Tasklet.dash` は Mesh RPC とは別に SlowDash の HTTP API を読み取るためのヘルパーです．

### Tasklet コールバックと実行単位

ユーザー向けの概念と詳しい使用例は [SlowMesh と SlowTask](SlowMesh_JP.md) を参照してください．SlowMesh は PubSub・RPC・Registry を提供する通信基盤，SlowTask は独立に実行されるスクリプト，`Tasklet` はスクリプトにライフサイクルと Mesh 接続を提供するアダプタです．`Mesh` 単体でも通信でき，その場合にタスク管理への登録やタスク仕様・ハートビートの送信が自動的に行われるわけではありません．

| デコレータ | ランタイムの動作 |
|---|---|
| `@tasklet.initialize()` | 初期化時に実行する．引数を受け取る関数にはタスクパラメータの辞書が渡る． |
| `@tasklet.finalize()` | 通常の終了処理で，実行中のタスクコールバックをキャンセルした後に実行する． |
| `@tasklet.once(delay=0)` | 初期化完了後，指定秒数の遅延を経て一度実行する． |
| `@tasklet.loop(interval=1, ticks=None)` | 周期的に実行する．整数の `ticks` は周期的な真偽値を引数として渡し，辞書なら `tick.store` などの名前付きフラグを渡す． |
| `@tasklet.schedule("08:00", use_utc=False)` | 指定時刻に実行する．カンマ区切りの `HH:MM` と `*` に対応し，UTC 指定がなければローカル時刻を使う． |
| `@tasklet.content("config/html-status")` | `_sd_get_content` RPC から要求時に呼ばれるコンテンツ生成関数を登録する．周期実行のコールバックではない． |

同じデコレータで複数の関数を登録できます．メイン処理のコールバックはそれぞれ asyncio タスクとして動きますが，Mesh 通信やハートビートとイベントループを共有します．一つのループコールバックは処理完了を待ってから次回を実行し，周期を超過しても同じコールバックを重複起動しません．ブロッキング I/O や `time.sleep()` はイベントループ全体を止めるので，非同期 I/O を使い，待機が必要なら `await asyncio.sleep()` を使います．強制終了やクラッシュでは finalize の実行は保証されません．

プロジェクト設定のタスクの `parameters` と CLI の `--parameters` JSON オプションは初期化パラメータを供給します．この辞書は，後から `/api/control` で渡す RPC 引数とは別です．コンテンツ生成関数と公開した制御ノードも別の仕組みで，前者は要求時にドキュメントを生成し，後者はリモートの get/set 操作で現在値を扱います．

## データオブジェクトモデル

SlowPy は，SlowDash 互換のデータに変換できる Python オブジェクトを提供します．

- スカラー値．
- `TimeSeries`．
- ヒストグラム．
- グラフ．
- トレンド．
- ツリー．
- テーブル．
- `slowdashify` による matplotlib 由来のデータ．

これらのオブジェクトは，タスク/ユーザーコード，ストレージへの書き込み，現在値データを配信する API で使われます．

### データオブジェクトの生成とデータ追加

データオブジェクトは，トップレベルの `slowpy` パッケージから生成し，通常はタスクのループ内で逐次データを追加していきます．

```python
import slowpy as slp

hist = slp.Histogram(100, 0, 10)         # [0, 10] を 100 ビンに分割
graph = slp.Graph(['channel', 'value'])

while not ControlSystem.is_stop_requested():
    value = device.read(...)
    hist.fill(value)
    graph.fill(channel, value)
```

各オブジェクトは `to_json()` を実装しており，これにより同じオブジェクトを現在値データとして配信したり（`ControlSystem.stream()` / `aio_publish()` を通じて），データストアに書き込んだりできます．`slp.RateTrend` のようなトレンド用のヘルパーは，移動窓に値を蓄積し，保存に適した `TimeSeries` を生成します．

```python
rate_trend = slp.RateTrend(length=300, tick=10)
rate_trend.fill(time.time())
datastore.append(rate_trend.time_series('rate'))
```

## 制御ノード

`slowpy/control/node.py` の `ControlNode` は，読み書き可能な制御エンドポイントの基底となる抽象です．

主なメソッドは次のとおりです．

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

非同期メソッドは，デフォルトでは同期メソッドに委譲します．`_is_thread_safe` が設定されている場合，同期版の `get()` と `set()` の呼び出しを `asyncio.to_thread()` 経由で実行できます．

### ノードチェーンの構築と get()/set() の利用

SlowPy は，外部システムやデバイスをすべて単一の制御ツリーに対応づけます．各ノードは `set()` と `get()` を持ち，名詞的な名前のメソッドは子ノードを返します．これらのアクセサを連ねたチェーンが，特定のエンドポイントへの論理的な経路を表します．

起点となるのは，通常は `ControlSystem` のインスタンス（または共有インスタンスの `control_system`）です．

```python
from slowpy.control import ControlSystem
ctrl = ControlSystem()

# ノードチェーンを構築する: Ethernet 接続 -> SCPI -> 特定のコマンド
device = ctrl.ethernet(host='192.168.1.43', port=5025)
Vout = device.scpi(append_opc=True).command('VOLT')
V    = device.scpi().command('MEAS:VOLT:DC')
```

チェーン中の各呼び出しが，1 つの枝を追加します．

- `ctrl.ethernet(...)` は TCP 接続のノードを開く（または再利用する）．
- `.scpi()` は，SCPI の設定を保持する子ノードを返す．
- `.command('VOLT')` は，チェーンを特定の SCPI コマンドに束縛する．

末端のノードを構築したら，`set()` で書き込み，`get()` で読み取ります．

```python
Vout.set(10)        # SCPI "VOLT 10;*OPC?" を送る
value = V.get()     # SCPI "MEAS:VOLT:DC?" を送り，応答を返す
```

`ControlNode` には，次のショートカットも定義されています．

- `node(value)` は `node.set(value)` と同じ．
- `node()` は `node.get()` と同じ．
- `node <= value` は `node.set(value)` を実行する．
- `float(node)`，`int(node)`，`str(node)`，`print(node)` は，暗黙的に `node.get()` を呼び出す．

非同期版は `await node.aio_set(value)` と `value = await node.aio_get()` で，後述の同期/非同期モデルを通じて，すべてのノードで利用できます．

枝はプラグインによって追加され，ルートの `ControlSystem` に限られません．プラグインは任意のノードに読み込めます．たとえば，Ethernet ノードに読み込まれたプロトコルプラグインは，Ethernet ノードの `set()`（送信）と `get()`（受信）を再利用するサブ枝を作ります．組み込みノード（Ethernet/SCPI/Telnet，HTTP，Shell，Slowdash，Redis など）の一覧と，それぞれの `set()` / `get()` の意味については，[Controls Script](ControlsScript.html) を参照してください．

`slowpy/control/control_*.py` 以下の制御モジュールは，デバイス，ネットワーク，メッセージ，シェル，HTTP，データストア，各種プロトコルとの具体的な連携を提供します．

### 同期版・非同期版の制御モジュール

ほとんどの連携は，`control_X.py` と `control_AsyncX.py` という同期版・非同期版のモジュールの組として提供されます．

```text
control_HTTP.py      / control_AsyncHTTP.py
control_Redis.py     / control_AsyncRedis.py
control_RabbitMQ.py  / control_AsyncRabbitMQ.py
control_MQTT.py      / control_AsyncMQTT.py
control_Modbus.py    / control_AsyncModbus.py
control_Slowdash.py  / control_AsyncSlowdash.py
control_Dripline.py  / control_AsyncDripline.py
```

一方の形式しか存在しない連携もあります．

- 同期版のみ: `control_Ethernet.py`，`control_UDP.py`，`control_Serial.py`，`control_VISA.py`，`control_Shell.py`，`control_DataStore.py`，`control_LabJackU.py`，`control_NanotechMotor.py`，`control_Microphone.py`，`control_DummyDevice.py` など．
- 非同期版のみ: `control_AsyncNATS.py`，`control_AsyncSlowMQ.py`，`control_AsyncLocalPubsub.py` など．

両者の違いは，入出力（I/O）メソッドの実装方法だけです．

- 同期版のモジュール（たとえば `control_HTTP.py` の `HttpNode`）は，`set()` / `get()` をオーバーライドし，`requests` のようなブロッキング型のライブラリを使います．
- 非同期版のモジュール（たとえば `control_AsyncHTTP.py` の `AsyncHttpNode`）は，`aio_set()` / `aio_get()` をオーバーライドし，`httpx` のようなノンブロッキング型のライブラリを使います．

どちらも `ControlNode` を継承するため，ノードツリーのモデル，子ノードのアクセサ，`readonly()` / `writeonly()` のラッパー，ヘルパーメソッド（`sleep()`，`wait()`，およびそれらの `aio_*` 版）を共通して持ちます．変わるのは末端の I/O 実装だけです．

### ノードツリーへの登録

各ノードクラスは，ファクトリ関数を返すクラスメソッド `_node_creator_method()` を定義します．`ControlNode.add_node()` はこの関数を親ノードクラスのメソッドとして注入し，その関数名が子ノードを生成するためのアクセサになります．同期版と非同期版では，通常は異なるアクセサ名を公開します．たとえば次のとおりです．

```text
HttpNode       -> node.http(url)
AsyncHttpNode  -> node.async_http(url)
```

`ControlNode.import_control_module(name)` は，現在の作業ディレクトリまたは `slowpy/control` ディレクトリから `control_<name>.py` を読み込み，`_node_creator_method()` を定義しているクラスを走査して，それらのアクセサをノードクラスに登録します．`ControlSystem.__init__()` は，次のデフォルトのモジュール群を読み込みます．

```text
Ethernet
HTTP
AsyncHTTP
Shell
DataStore
```

それ以外のモジュールは，タスクコードやユーザーコードから必要に応じて読み込みます．たとえば `ControlSystem().import_control_module('Redis')` のようにします．

### 非同期フォールバックとの関係

基底の `ControlNode` は，同期版の `set()` / `get()` に委譲するデフォルトの `aio_set()` / `aio_get()` をあらかじめ提供しています（直接呼び出すか，`_is_thread_safe` が設定されている場合は `asyncio.to_thread()` 経由で呼び出します）．このため，同期版のみのモジュールでも，非同期コードから利用できます．専用の `control_Async*.py` モジュールは，長時間維持するネットワーク接続やメッセージブローカーとの接続など，真にノンブロッキングな I/O が重要になる場合のために用意されています．これは，前述したサーバー側の `DataSource` の同期/非同期の二重メソッドや，`_NoAsync` データソースプラグインと同じ考え方です．

## データストア

SlowPy のデータストアは，書き込み側のストレージヘルパーを提供します．

`store/factory.py` は，URL を実装にマッピングします．

```text
postgresql:// -> DataStore_PostgreSQL
mysql://      -> DataStore_MySQL
sqlite://     -> DataStore_SQLite
influxdb2://  -> DataStore_InfluxDB2
redis://      -> DataStore_Redis
csv:///       -> DataStore_CSV
dump:///      -> DataStore_TextDump
```

`DataStore` は，次の操作に対応します．

```text
append(values, tag=None, timestamp=None)
update(values, tag=None, timestamp=None)
close()
```

値には，スカラー，フィールドの辞書，データ要素，`TimeSeries` を使えます．

### データの書き込み

ストアは，クラスから直接生成するか，`store/factory.py` の `create_datastore_from_url()` を使って URL から生成します．

```python
from slowpy.store import DataStore_PostgreSQL

datastore = DataStore_PostgreSQL(
    'postgresql://postgres:postgres@localhost:5432/SlowTestData',
    table='SlowData'
)

while True:
    datastore.append(value, tag='voltmeter')      # チャンネルタグを付けた単一の値
    datastore.append({'ch00': v0, 'ch01': v1})    # チャンネル/値のペアの辞書
```

`append()` は新しい時系列レコードを追加し，`update()` は直前の値を上書きして最新の値だけを残します．この違いは，ヒストグラムのようなデータ要素オブジェクトを扱う際に意味を持ちます．

```python
datastore.append(hist, tag='spectrum')   # ヒストグラムの時系列（時刻ごとに 1 つ）
datastore.update(hist, tag='spectrum')   # 最新のヒストグラムだけを残す
```

SQL 系のストアでは，デフォルトで UNIX タイムスタンプを用いた「ロングフォーマット」が使われます．異なるテーブル構成が必要な場合は，ユーザー定義の `TableFormat` でスキーマや INSERT 文を上書きできます．

# SlowDash にとって重要な Slowlette の内部仕様

SlowDash のいくつかの挙動は，Slowlette の設計に直接依存しています．

### 同一ルートに複数のハンドラが応答できる

Slowlette は，アプリツリー内の一致するすべてのハンドラを意図的に呼び出します．このため，複数のコンポーネントが `/api/config`，`/api/channels`，`/api/data/{channels}` を提供できます．

### レスポンスのマージはアプリケーションモデルの一部である

マージされたレスポンスは，単なる便利機能ではありません．独立に開発されたコンポーネントやプラグインから集約型の API レスポンスを組み立てるための仕組みです．

### コンポーネントの順序には意味がある

独自のレスポンスが後続のレスポンスをマージできるため，`slowdash.py` における組み込み順序は実行時の挙動の一部です．

### 内部 API 呼び出しも同じルーターを使う

`App.request()`，`request_config()`，`request_channels()`，`request_data()` は `self.slowlette(...)` を直接呼び出し，HTTP リクエストと同じルーティングとレスポンスマージを使います．Mesh の pub/sub と RPC は，これとは別の通信経路です．

# 主要フローのまとめ

### 起動

```text
slowdash.py
  -> App
  -> Project
  -> sys.path / cwd setup
  -> include components
  -> ASGI/WSGI/CGI/CLI dispatch
  -> post_startup: Mesh connections, task discovery / auto-start
```

### API リクエスト

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

### データ読み取り

```text
/api/data/{channels}
  -> data source plugins
  -> user hooks / remote task nodes / WebMesh cache / registry values
  -> merged JSON data
```

### 設定の読み取り

```text
/api/config
  -> each component public_config()
  -> deep-merged JSON config
```

### 現在値データ

```text
Mesh.aio_publish() / POST /api/webmesh/publish/{topic}
  -> Mesh transport / broker
  -> WebMesh cache and browser SSE
  -> registry pubsub cache
```

### プラグインの読み込み

```text
project config
  -> PluginComponent
  -> app/plugin module lookup
  -> class lookup
  -> plugin instance
  -> Slowlette include
```

# 開発上の実務的な注意

- 新しい API コンポーネントを追加する場合は，`Component` をサブクラス化し，`slowdash.py` から組み込む．
- 新しいデータソースを追加する場合は，新しい `app/plugin/datasource_*.py` ファイルで `DataSource` をサブクラス化する．
- 新しいエクスポータを追加する場合は，`export_*.py` プラグインを追加する．
- 他のコンポーネントと集約させたいエンドポイントでは，辞書やリストのコンテンツを返してレスポンスのマージを利用する．
- 後続のコンポーネントの出力を加工したいエンドポイントでは，独自の `slowlette.Response` サブクラスを返し，`merge_response()` をオーバーライドする．
- `public_config()` には秘密情報を入れない．`/api/config` はクライアントに公開される．
- コンポーネントの組み込み順序の変更には注意する．マージの挙動が変わる可能性がある．
- サーバー側のコードを外部 API クライアントと同じルートロジックで動かしたい場合は，内部の `App.request*()` ヘルパーを使う．

- Mesh タスクを追加する場合は，`Tasklet` と `mesh.export()` を使い，`slowdash-task` または独立プロセスから実行する．
- ブラウザ配信は WebMesh の SSE，Mesh トランスポートは SlowMQ などのブローカー，共有状態は Mesh レジストリという役割分担を保つ．
