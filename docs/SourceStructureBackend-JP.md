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
    - ユーザー/タスクモジュール API
    - エクスポート API
    - ユーザー HTML/コンテンツ API
    - リアルタイム/現在値データの補助機能
    |
    v
プラグインとライブラリ
    - app/plugin のデータソースとエクスポータ
    - slowpy のデータオブジェクト，制御ノード，ストア，クライアントヘルパー
```

中心となるサーバーオブジェクトは，`app/server/slowdash.py` の `App` です．`App` は `slowlette.App` を継承し，`Project` を生成して実行環境を整えたうえで，SlowDash の各コンポーネントを Slowlette のルーターに組み込みます．

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
- `sd_taskmodule.py`: 現行のプロセス内タスクモジュールシステム．
- `sd_userhtml.py`: ユーザー提供の HTML/コンテンツの配信．
- `sd_console.py`: コンソール/標準出力のキャプチャ．
- `sd_misc_api.py`: その他の組み込み API エンドポイント．
- `sd_mesh.py`: 現在値データのキャッシュと，選択したトピックへの websocket 接続．
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
- `middleware.py`: ミドルウェアのサポート．

### `lib/slowpy`

SlowPy は，データ型，制御の抽象化，ストレージへの書き込み機能，クライアントヘルパー，作図ヘルパーを提供します．

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

# アプリケーションの起動フロー

## コマンドラインまたはサーバーの起動

主要なエントリーポイントは `app/server/slowdash.py` です．

通常の起動シーケンスは次のとおりです．

1. コマンドラインオプションを解析する．
2. `App(project_dir, project_file, is_cgi, is_command, is_async)` を生成する．
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

この順序は重要です．Slowlette は，一致した複数のハンドラからレスポンスを集めてマージします．そのため，先に組み込まれたコンポーネントがマージ用のラッパーを担い，後続のコンポーネントがマージ対象のコンテンツを提供できます．

コード中で示されている順序の意図は次のとおりです．

- `ConsoleComponent` は，標準出力を早い段階でキャプチャするため，最初に組み込まれる．
- `MeshComponent` は，そのキャッシュがデータソースの応答を補えるよう，データソースより前に組み込まれる．
- `UserModuleComponent` と `TaskModuleComponent` は，ユーザー/タスクモジュールが API に関与したりデータソースを生成したりできるよう，`DataSourceComponent` より前に組み込まれる．

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
@slowlette.on_event('startup')
```

`router.py` の `PathRule` は，デコレートされた関数のシグネチャを調べ，次のものをバインドします．

- `{channels}` のようなパスパラメータ．
- 名前で一致するクエリパラメータ．
- `bytes` のリクエストボディ．
- JSON ボディのラッパー．
- リクエスト全体を表す `Request`．
- `WebSocket`．
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

## `TaskModuleComponent`

`sd_taskmodule.py` は，現行のプロセス内タスクモジュールシステムです．

ユーザーモジュールの機構を拡張し，タスクコマンドの解析，コマンドの実行，`ControlSystem` との統合を追加します．

主なルートは次のとおりです．

```text
GET  /api/control/task
POST /api/control
POST /api/control/task/{taskname}
GET  /api/channels
GET  /api/data/{channels}
POST /api/consume/current_data
```

タスクコマンドの流れは次のとおりです．

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

エクスポートされた制御ノードは現在値チャンネルとして公開され，`/api/data/{channels}` から読み取れます．受信した現在値データのメッセージは，`/api/consume/current_data` を通じてエクスポート済み変数の設定にも使えます．

## `UserHtmlComponent`

`sd_userhtml.py` は，ユーザー提供の HTML と関連コンテンツを配信します．また，ユーザー URL を内部の設定/コンテンツ API へリダイレクトまたはマッピングします．

これにより，プロジェクト固有の UI ページを，コアサーバーを変更することなく，プロジェクトの設定/コンテンツ領域に置けます．

## `MeshComponent`

`sd_mesh.py` は，`/api/consume/current_data` を通じて受け取った現在値データのキャッシュを保持します．

主な役割は次のとおりです．

- 選択したトピックへの websocket 接続．
- `/api/emit/{topic}` の再配信と，websocket への転送．
- 現在値データのキャッシュ．
- キャッシュに基づく現在値チャンネルによる `/api/channels` の補完．
- 最新のキャッシュ値による `/api/data/{channels}` の補完．

このコンポーネントはデータソースより前に組み込まれます．そのため独自のレスポンスが，後続のデータソースの応答とキャッシュデータをマージできます．

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

## その他のコンポーネント

その他のサーバーコンポーネントは次のとおりです．

- `ConsoleComponent`: 表示や API での利用のためにコンソール出力をキャプチャする．
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

最も一般的な読み取り経路は次のとおりです．

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

`/api/data/{channels}` では，`DataSource` プラグインが SlowDash のデータモデル形式でデータを返します．キャッシュコンポーネントは，次の条件を満たす場合に現在値を追加できます．

- 要求されたチャンネルがキャッシュ対象である．
- キャッシュのタイムスタンプが，要求された時間範囲に入っている．
- 既存のレスポンスが存在しないか，キャッシュ値より古い．

# 書き込み・配信・現在値データのフロー

現在値データの更新は，次の経路で SlowDash に入ります．

```text
POST /api/emit/{topic}
POST /api/consume/current_data
internal app.request_emit(topic, message, sender=...)
```

典型的な流れは次のとおりです．

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

`sender` パラメータは，タスク自身が配信した値が同じタスク変数のパスに反射して戻ってくるのを防ぐために使われます．

# 制御フロー

制御コマンドは `/api/control` を使います．

現行のプロセス内タスクの流れは次のとおりです．

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

ユーザーモジュールも，定義したフックに応じてコマンド処理に参加できます．

# SlowPy ライブラリの役割

SlowPy は，サーバー側のコンポーネントとユーザーコードの両方から使われます．

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

`App.request()`，`request_config()`，`request_channels()`，`request_data()`，`request_emit()` は `self.slowlette(...)` を直接呼び出します．このため，サーバー側のプロデューサ/コンシューマも，外部の HTTP クライアントと同じルーティングおよびレスポンスマージのモデルを使います．

# 主要フローのまとめ

### 起動

```text
slowdash.py
  -> App
  -> Project
  -> sys.path / cwd setup
  -> include components
  -> ASGI/WSGI/CGI/CLI dispatch
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
  -> optional user/task/current-data additions
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
/api/emit/current_data
  -> /api/consume/current_data
  -> cache update and variable update hooks
  -> websocket forwarding where applicable
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
