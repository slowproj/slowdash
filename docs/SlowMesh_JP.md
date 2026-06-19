---
title: SlowMesh と SlowTask
---

# 概要

<img src="fig/SlowMeshConcept.png" width="40%">
<img src="fig/SlowMesh-SlowTask.png" width="40%">

## SlowMesh
SlowMesh は，SlowDash の各コンポーネント（SlowDash サーバーと各種 SlowTask）が協調動作するための通信基盤です．
メッセージングバックボーンを下位通信層として使用し，その上に PubSub，RPC，Registry (Key-Value Store) の機能を提供します．
メッセージングバックボーンには，SlowDash が提供する組み込みの SlowMQ の他，NATS や MQTT，Redis，RabbitMQ などの広く使用されている外部システムをそのまま使うこともできます．

SlowMesh は以下の３つの通信を提供します．

- **PubSub**: SlowPy Control に実装されているメッセージングバックボーンインターフェースへの薄い統一ラッパー
- **Remote Procedure Call (RPC)**: PubSub の上に構築された遠隔関数呼び出し
- **Registry (Key-Value Store)**: RPC を使って実装された共有名前空間

## SlowTask
SlowTask は SlowMesh の上で独立にかつ協調して動く実行単位（おおまかには，一つの Python スクリプト）です．
プロセスまたは動的ロードモジュールのいずれかとして実行できます．

SlowTask には以下の機能が実装されています．

- 開始時・終了時や，一定時刻，一定時間間隔でのユーザー関数呼び出し
- SlowMesh による通信（関数のエクスポートやデータの送り出し）
- HTTP 経由での SlowDash サーバーとの通信（構成情報の取得など）



# SlowMesh
## 構成要素
### SlowPy Mesh ライブラリ
SlowTask スクリプトから使用されるライブラリです．

- `slowpy.mesh.Mesh`: SlowMesh 通信機能へのインターフェース
- `slowpy.mesh.Tasklet`: Python スクリプトを SlowMesh 上の独立タスク (SlowTask) として実行するためのアダプタ


### SlowDash Mesh サービス
SlowDash サーバー内で SlowMesh 関連のサービスを行うものです．

- Registry (Key-Value Store) サービス
- Web API (HTTP POST による publish や WebSockets 経由の PubSub など）

### SlowMQ バックボーン
SlowDash 内蔵の PubSub ブローカーです．SlowDash のサーバープロセスに含まれているので，何も設定せずにそのまま使用できます．
WebSockets で実装されています．


## PubSub
### 使用例
典型的には，SlowMesh は後述の Tasklet によって構築されたものを使います．

##### Publish
```python
topic = 'data.temp0'
data = { 't': t, 'x': temp0 }
await tasklet.mesh.aio_publish(topic, data)
```

##### Subscribe
```python
@tasklet.mesh.on('data.>')  # メッセージ受信時のコールバックを指定
async def handle_data(headers, data):
    topic = headers.get('topic')
    ...
```

### バックボーン接続
SlowPy Mesh の PubSub は，SlowPy Control に実装されているメッセージングバックボーンへのインターフェスに対する薄いラッパーです．
SlowPy Control にある以下のメッセージングシステムを選べます：

| バックボーン | SlowPy モジュール | ブローカー | 備考 |
|---|---|---|---|
| SlowMQ | control-AsyncSlowMQ.py | 不要 (SlowDash 組み込み) | HTTP(S) ベースで，ファイアウォールを超えてアクセス可能 |
| NATS | control-AsyncNATS.py | 別に NATS Broker が必要 | |
| MQTT | control-AsyncMQTT.py | 別に MQTT Broker（eclipse-mosquitto など）が必要 | 
| RabbitMQ | control-AsyncRabbitMQ.py | 別に RabbitMQ Broker が必要 | |
| Redis-PubSub | control-AsyncRedis.py | 別に Redis サーバーが必要 |トピックフィルタに制限あり |

使用するバックボーンサービスは，Mesh のコンストラクタ（または `connect()` 関数）に渡される URL により指定されます：

| バックボーン | URL 形式 |
|---|---|
| SlowMQ (HTTP または HTTPS 上の WebSockets)| `slowmq://HOST:PORT` (HTTP) または `slowmqs://HOST:PORT` (HTTPS) |
| NATS | `nats://HOST` |
| MQTT |  `mqtt://HOST` |
| RabbitMQ |  `rabbitmq://USER:PASS@HOST/EXCHANGE` |
| Redis-PubSub |  `redis://HOST/DB` |

認証情報が必要なら，`HOST` の直前に `USER:PASS@` を挿入してください．

### トピックフィルタ
NATS に準じたフィルタを使用できます．

- 階層区切り文字は `.`
- `*` は任意の一階層にマッチ
- `>` は任意数の末尾にマッチ（最後の文字としてのみ使用可能）

SlowMQ と NATS 以外のバックボーンが使用された場合，これらの特殊文字は置き換えられてからライブラリに渡されます．厳密な階層を採用しない Redis の場合，フィルタの動作が変わる場合があります．

| バックボーン  | 階層区切り文字 | 一階層マッチ | 任意数末尾階層マッチ | 例1 | 例2 |
|--------------|--------------|------------|--------------------|---|--|
| (元の文字)    | `.`          | `*`        | `>`                | `data.store.>` | `data.*.HV.ch100` |
| SlowMQ       | `.`          | `*`        | `>`                | `data.store.>` | `data.*.HV.ch100` |
| NATS         | `.`          | `*`        | `>`                | `data.store.>` | `data.*.HV.ch100` |
| MQTT         | `/`          | `+`        | `#`                | `data/store/#` | `data/+/HV/ch100` |
| RabbitMQ     | `.`          | `*`        | `#`                | `data.store.#` | `data.*.HV.ch100` |
| Redis-PubSub | `:`          | `*` (近似動作) | `*`  （近似動作）| `data:store:*` | `data:*:HV:ch100` |

トピック名に `/` や `#` などを含めると，これらを特殊文字としているバックボーンを使用した場合に問題を引き起こします．
これらの文字の使用は避けた方がいいです．

なお，Mesh のコンストラクタオプションで，これらの文字割り当てを変えることができます．例えば，MQTT を中心に運用することが確定しているのであれば，SlowMesh においても MQTT と同じ特殊文字を割り当てておくことができます．

## Remote Procedure Call (RPC)
RPC は，ある SlowTask が公開した Python 関数を，他の SlowTask から名前で呼び出すための仕組みです．
PubSub 上の `sd.rpc`/`sd.rpc_reply` トピックで実装されています．
呼び出し側は `reply_to` に自分宛ての返信トピック `sd.rpc_reply.{MeshID}` を指定し，`sd.rpc.{モジュール名}` にリクエストを publish します．実行側は，リクエストの `reply_to` で指定されたトピックに返信データを publish します．

- 実行側：`@mesh.export` デコレータで関数を export
- 使用側：`mesh.aio_call(name, *args, **kwargs)` で呼び出し

### 使用例
##### 実行側
```python
@tasklet.mesh.export
async def chat(line, *, sender=None):
    print(f'You ("{sender}") sent me "{line}".')
    print(f'I will send you the current time.')
    return str(datetime.datetime.now())
```

- 現時点で，return value に返せるのは JSON にシリアライズできる値のみです．
- RPC は 1 秒程度を上限に return してください．呼び出し側はデフォルトで 5 秒でタイムアウトします．
- 時間がかかる処理は，キューに入れるか，非同期タスクまたはスレッドなどで実行するようにしてください．

##### 使用側
```python
    return_value = await tasklet.mesh.aio_call('test-mesh-rpc.chat', line, sender='me')
```

- 最初の引数が `モジュール名.関数名` で，それ以降の引数が遠隔関数の引数にそのまま渡されます．
- 現時点で，引数に渡せるのは JSON にシリアライズできる値のみです．
- エラーが発生した場合は Exception が投げられます．
- デフォルトのタイムアウト時間は，Mesh のコンストラクタパラメータで指定できます．また，`aio_call_many()` 関数を使えば，呼び出しごとに個別のタイムアウトを設定することもできます．

### ControlNode のエクスポート
RPC を使って ControlNode のリモートアクセスも実装されています．

##### 実行側
```python
from slowpy.control import ControlNode

class MyNode(ControlNode):
    def aio_set(self, value):
        ...
    def aio_get(self):
        return ...
    
tasklet.mesh.export(node_name, MyNode())
```

##### 使用側
```python
    node = tasklet.mesh.remote_node(f'{module_name}.{node_name}')
    await node.aio_set(value)
    print(await node.aio_get())
```


## Registry (Key-Value Store)
Registry は，複数の SlowTask が共有する名前付きの値置き場です．状態，設定値，処理要求などをプロセス間で共有する用途を想定しています．
`sd_mesh_registry.py` モジュールに対する RPC で実装されています．

レジストリには，Mesh が保持している `Registry` クラスのインスタンス `registry` を経由してアクセスします：
```python
    registry = tasklet.mesh.registry

    # 値のセット
    await registry.aio_set('mysetup/run/number', run_number)
    
    # 値の取得
    run_number = await registry.aio_get('mysetup/run/status')
```


Registry には，以下のメソッドがあります：

- 書き込み (set)： `async def aio_set(self, key, value, *, cas_revision=None) -> int|None`
- 読み出し (get)： `async def aio_get(self, key:str, default:Any=None, *, with_meta:bool=False) -> Any`
- キー一覧 (keys)： `async def aio_keys(self, prefix:str='', limit:int|None=1000)->list[str]`
- 削除 (delete)： `async def aio_delete(self, key:str, *, cas_revision=int|None) -> bool`

**Key**:
階層区切り文字を除いて，Python や C++ などにおける識別子（変数名とか）と同じ感じの名前を使用してください．具体的には，英数字またはアンダースコアだけで構成され，かつ，最初の文字に数字は使用できません．

**Value**:
Value には，現時点では JSON にシリアライズできる値に限られます．

**階層構造**:
Registry の内部は，単純な Key-Value Store です．Key は単純な文字列で，階層構造は SlowMesh では規定していません．ユーザが選んだ任意の階層区切り文字（ただし「識別子」として使えない文字のみ）を使うことを想定していますが，特に理由がなければ `/` による区切りを使用してください．
階層区切り文字にはアルファベット，数字，アンダースコアは使用できません．某 OS で行われているように，バックスラッシュなどの特殊文字を使用することも避けたほうが無難です．特に理由がなければ，`.`，`:`，`/` あたりから選ぶのがいいです．

```python
    registry = tasklet.mesh.registry
    
    await registry.aio_set('user', 'slowuser')
    await registry.aio_set('state/run/mode', 'physics')
    await registry.aio_set('state/run/number', 123)
    await registry.aio_set('state/run', 'running')    # 注：この例はあまり良くない．'state/run/status' に入れる方がいい

    print(await registry.aio_keys('state/run'))       # -->  ['state/run/mode', 'state/run/number', 'state\run']
    print(await registry.aio_get('state/run/mode'))   # -->  physics
    print(await registry.aio_get('state/run'))        # -->  running
    print(await registry.aio_get('state/run/'))       # -->  {'mode': 'physics', 'number': 123, '$value': 'running'}
    print(await registry.aio_get('/'))                # -->  {'user': 'slowuser', 'state': {'run': {'mode': 'physics', 'number': 123, '$value': 'running'}}}
```

最後の２つの例にあるように，`Registry.aio_get(key)` メソッドにおいて，key の最後の文字が英数字またはアンダースコアでない場合，その文字を階層区切り文字と解釈し，key の階層以下のすべての値を階層構造にまとめて，結果を dict として返します．

`state/run` のように，ある key に値が割り当てられていて，かつ，その下に階層がある場合は，そのままでは自然な dict や JSON に変換できません（ノードが値と子ノードの両方をもつことができないため）．そのような場合，値は `$value` フィールドに格納されます．

レジストリの階層構造はどの区切り文字を使うかも含めてユーザーが自由に設計できますが，JSON として表現できる形に留める（子ノードがあるところに値を記録しない）のがおすすめです．上記の例では，`registry.set('state/run', 'running')` を`registry.set('state/run/status', 'running')` などとすれば，この問題を回避できます．

Registry では，更新値の上書きを防ぐため，CAS (Compare-And-Set) オプションを備えています．

- レジストリ値のメタデータには，書き込み回数を数える CAS Revision が割り当てられる
- `aio_set()` で CAS Revision はインクリメントされ，新しい CAS Revision が返される
- `aio_set()` で `cas_revision` オプションが None でない場合，保持されている値の CAS Revision と一致しないと，書き込みに失敗する
  - これにより，自分が設定した値を，他の誰かが書き換えた場合に，それを知らずに上書きすることを避けられる．
- `aio_delete()` も同様．CAS Revision が一致しなければ削除しない．

`aio_set()` の `with_meta` オプションを `True` にすると，書き込み時刻や CAS Revision などを含んだ Meta Data が返されます：
```json
{
    "key": キー,
    "value": 値,
    "revision": CAS Revision,
    "updated": 最終書き込み時刻
}
```

レジストリに記録された値は，SlowDash App から，データベース上のデータと同じ形式(同じ Web API と同じ戻り値フォーマット)で読むことができます．
channel 名に `@registry:{key}` を指定してください．
```console
$ curl "http://localhost:18881/api/data/@registry:state/run/"
{
    "@registry:state/run/": {
        "start": 1781858837.4758086,
        "t": 3600.0,
        "x": {"tree": {"$value": "running", "mode": "physics", "number": 123}}
    }
}
```

レジストリの key の先頭に区切り文字を付加しないように注意してください（この例では `@registry:/state/run/` は誤り）．SlowMesh の Key-Value Store において，区切り文字は特別な意味を持たない（get() で dict への整形に利用されるだけ）ため，先頭に区切り文字があると別の key になってしまいます．


# SlowTask
SlowTask は SlowMesh の上で独立にかつ協調して動く実行単位（おおまかには，一つの Python スクリプト）です．プロセスまたは動的ロードモジュールのいずれかとして実行できます．

## SlowTask の組み込み
```python
from slowpy.mesh import Tasklet
tasklet = Tasklet()

...(本文)...

if __name__ == '__main__':
    tasklet.run(slowdash_url='http://localhost:18881')
```

SlowTask はシングルスレッドの非同期呼び出しで全体が並列に動くので，スクリプトの中で **`time.sleep()` を使うと全体が固まってしまいます**．
以下の `@tasklet.loop(interval)` を使ってループを書くことにより，明示的な sleep をしないのが想定です．
どうしても sleep をする場合は，`await asyncio.sleep()` または `await control_system.aio_sleep()` を使ってください．

## SlowTask の機能
### Lifespan コールバック
tasklet が提供するデコレータにより，特定のタイミングや一定時間間隔に SlowTask 中の関数を呼び出すことができます．
同じデコレータを複数回使用することもできます．
特に，`@tasklet.loop(interval)` を小さい単位に複数使うことにより，スクリプトの中のループを避けることができて，スリープや終了処理などに伴う煩雑さを避けることができます．

- `@tasklet.initialize()`: スクリプト開始時に呼ばれる
- `@tasklet.finalize()`: スクリプト終了時に呼ばれる
- `@tasklet.once(delay:float=0)`: initialize から指定秒数後に呼ばれる
- `@tasklet.schedule(time:str, use_utc:bool=False)`: 指定時刻に繰り返し呼ばれる
   - `time` は `HH:MM:SS` 形式．
   - `HH` および `MM` に `*` を使って毎時または毎分実行を指定できる．
   - `,` で区切って複数の時刻を並べることができる．
   - 例)
     - `@tasklet.schedule("*:00")`: 毎時０分
     - `@tasklet.schedule("08:00")`: 毎朝８時
     - `@tasklet.schedule("*:00,*:20,*:40")`： 毎時３回
     - `@tasklet.schedule("00:00,08:00,16:00", use_utc=True)`: 一日３回（夏時間切り替え対応）
- `@tasklet.loop(interval:float)`: 指定秒数間隔で繰り返し呼ばれる

### SlowMesh 機能
#### PubSub によるメッセージ交換
現時点では，データおよびヘッダに渡せる値は，JSON にシリアライズできるものに限られます．
<br>（TODO: バイナリをサポート）

- データを publish: `await tasklet.mesh.aio_publish(name:str, data, headers={})` (async メソッド)
- データに subscribe: `@tasklet.on(topic:str)` （デコレータ）

#### Registry (Key-Value Store) へのアクセス
- 書き込み (set)： `await tasklet.mesh.registry.aio_set(key, value, *, cas_revision=None) -> int|None`
- 読み出し (get)： `await tasklet.mesh.registry.aio_get(key:str, default:Any=None, *, with_meta:bool=False) -> Any`
- キー一覧 (keys)： `await tasklet.mesh.registry.aio_keys(prefix:str='', limit:int|None=1000)->list[str]`
- 削除 (delete)： `await tasklet.mesh.registry.aio_delete(key:str, *, cas_revision=int|None) -> bool`

#### 関数および変数のエクスポート
- 関数のエクスポート： `@tasklet.mesh.export`  (デコレータ)
- 関数を指定した名前でエクスポート： `@tasklet.mesh.export(name:str)`  (デコレータ)
- SlowPy Control Node のエクスポート： `tasklet.mesh.export(name:str, node:slowpy.control.ControlNode)` （メソッド）

**エクスポートした関数の実行は，即座に終了するようにして，最大 1 秒を目安に return するようにしてください**．
呼び出し側は数秒程度でタイムアウトをします．
時間がかかる処理は，以下の方法を検討してください：

- 処理要求を変数にセットするか `asyncio.queue` に入れて，`@tasklet.loop()` でそれを見て処理を開始する
- `asyncio.create_task()` に投げる
- TODO: `@export()` に `threading=True` オプションを指定して，バックグラウンドスレッドを自動生成するようにする

処理結果は publish し，エラーの場合は alert を publish するまたはログに書く，というのが想定です．
必要に応じて，処理状況を逐次 publish するか，Registry に状態を記録するなどずれば，呼び出し側が状況を把握できます．
高信頼が必要な場合の高度な方法として，`sd.rpc.>` を subscribe して，システムが期待する状態に遷移するかを監視する SlowTask を走らせるという手もあります．

### SlowDash Mesh サービスへのインターフェース
その他，SlowMesh の接続に必要な内部処理も行っています．

- Heartbeat の送り出し
- 仕様問い合わせ (`sd.task.introduce`) への応答


## SlowTask の実行
SlowTask のスクリプトは，独立プロセス (task process) として走らせることも，SlowDash のサーバープロセスに動的ロードして (task module) 走らせることもできます．

### 独立プロセス (task process)

### 動的ロードモジュール (task module)


## スクリプト中で明示的に Tasklet を使用しない場合
スクリプト中で明示的に Tasklet を使用しない場合でも，任意の Python スクリプトを SlowTask として実行（task process）または動的ロード(task module)をすることができます．この場合は，以下の機能のみが使用できます．

- 古いスタイルの Lifespan Callbacks (`_initialize()` / `_run()` / `_loop()` / `_finalize()`)
- すべての関数の Export
- Start/stop コントロール (task module のみ)


# Example Projects
SlowTask の基本的な機能を使用する例が `ExampleProjects/Experimental/Mesh/` にあります．

- `slowtask-randomwalk.py` がダミーデータを生成して `data.store.HV.ch0` に publish
- `slowtask-store.py` が `data.store.>` を subscribe して，受け取ったデータを SlowPy DataStore に保存
- `slowtask-randomwalk.py` に対するブラウザから RPC 経由の set point 設定
- `slowtask-randomwalk.py` に対するブラウザから pubsub 経由の start/stop コントロール

現時点では，この例は Task Process としてのみ使用可能です．
２つの Task Process と SlowDash サーバ用に３つのターミナルを開いて，それぞれ以下のコマンドを実行してください．
どれを先に実行しても大丈夫なように作ったつもりですが，気持ち悪ければ以下の順にしてください．

```console
$ cd PATH/TO/PROJECT
$ slowdash --port=18881
```
```console
$ cd PATH/TO/PROJECT/config
$ slowdash-activate-venv
$ python slowtask-store.py
```
```console
$ cd PATH/TO/PROJECT/config
$ slowdash-activate-venv
$ python slowtask-randomwalk.py
```
すべて実行したら，10秒ほど待ってからブラウザで `http://localhost:18881` に接続してください．
（すでに表示しているなら，ページのリロードをしてください．）

現時点では，SlowDash のポート番号などはスクリプト中にハードコーディングしています．
SlowMesh/SlowTask の開発状況に応じて徐々に改善していきます．


# HTTP API
## SlowTask

SlowTask への HTTP API は Slowlette を経由して `sd_taskprocess.py` コンポーネントにより実装されています．

### GET `api/task/specs`
Task Spec の一覧を返す

### POST `api/control`
Mesh メッシュリクエスト

- Body は HTML の Form 入力値の JSON ドキュメント（フォーム中の `<input>` の `name` と `value` を集めた object）
- `type="submit"` の `<input>` エレメントの `name` をリクエストと解釈する

#### RPC Call Request (旧形式の slowtask function call と互換)
- Syntax: `タスク名.関数名(固定パラメータリスト)`
- Example: `<input type="submit" name="run_controller.start(run_mode='normal')">`
- Form 中の `type="submit"` 以外の `<input>` 要素の `name` と `value` に固定パラメータを追加したものが RPC の引数に渡される．
- TODO: RPC のシグニチャを見て，必要なパラメータのみを選んで，型チェック・型変換もする
- レスポンス：
  - 成功： 200, `{ "status": "ok", "return_value": return_value }`
  - RPC エラー (呼び出し先例外)： 200, `{ "status": "error", "message": error_message }`
  - RPC キャンセル (呼び出し先 Async-Task Cancelled)： 200, `{ "status": "cancelled" }`
  - その他エラー: 400 番台のエラーレスポンス

#### Publish Request
- Syntax: `publish トピック名(固定パラメータリスト)`
- Example: `<input type="submit" name="publish my_setup.start(run_mode='normal')">`
- Form 中の `type="submit"` 以外の `<input>` 要素の `name` と `value` に固定パラメータを追加した Key-Value Pairs の JSON obect が publish される．
- レスポンス：
  - 成功： 200, `{ "status": "ok" }`
  - エラー: 400 番台のエラーレスポンス


## Registry (Key-Value Store)

Registry への HTTP API は Slowlette を経由して `sd_mesh_registry.py` コンポーネントにより実装されています．

### GET `api/registry/value?key={key}`
Registry に保持されている値を返す（メタデータを含む JSON ドキュメント）

### GET `api/registry/keys?prefix={prefix}&limit={limit}`
Registry に保持されているキーのリストを返す

### GET `api/data?ch={channel}&length={lengh}&to={to}`
Registry に保持されているキーの値をデータとして返す（データベースからのデータと同形式）．

- channel が `@registry:{key}` となっているものが対象
- TODO: レジストリメタデータの [updated, now()] とデータクエリ期間が重なるものが対象


# RPC サービス
## Registry (Key-Value Store)
- モジュール名： `sd_mesh_registry`
- エクスポート関数：
  - 書き込み： `async def aio_set(self, key, value, *, cas_revision=None) -> int|None`
  - 読み出し： `async def aio_get(self, key:str, default:Any=None, *, with_meta:bool=False) -> Any`
  - キー一覧： `async def aio_keys(self, prefix:str='', limit:int|None=1000)->list[str]`
  - 削除： `async def aio_delete(self, key:str, *, cas_revision=int|None) -> bool`


## Task RPC
- モジュール名： `{task_name}` (デフォルトで，スクリプトファイル名が `slowtask-{task_name}.py`)
- エクスポート関数： Task Script 中で `@export` したもの



# PubSub トピック構成
## sd.task
- すべての SlowTask Process は `sd.task.control.>` を subscribe すること．

### sd.task.heartbeat.{task_name}
Task の生存信号．Headers のメタデータのみで，Body は空．

##### 主な用途
- Sender(s): task process
- Receiver(s): sd_taskprocess (SlowDash サーバー)，モニタサービス
- Timing:
  - 指定時間間隔（`Tasklet._heartbeat_interval`，１０秒）
  - Tasklet のメインループから送出（コルーチンやスレッドではない；必ずメインと一緒に停止する）

##### 第２用途
- サーバークラッシュなどによる PubSub の接続断後の再接続は publish にトリガされるので，heartbeat 送り出しが接続断後の reconnect retry になる
- Reconnect により，`sd.task.spec` 再送などもトリガされる
- サーバー復帰後のシステム再開は，heartbeat interval 程度遅れることになる


##### JSON Schema
Headers:
```json
{
    "type": "object",
    "required": [ "mesh_id", "name", "timestamp"],
    "properties": {
        "mesh_id": { "type": "string" },
        "name": { "type": "string" },
        "timestamp": { "type": "int" }
    }
}
```

Body:
```json
{}
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

### sd.task.spec.{task_name}
タスクが外部公開している関数と変数の一覧

##### 主な用途
- Sender(s): task process
- Receiver(s): sd_taskprocess (SlowDash サーバー)
- Timing:
  - タスクが開始したとき
  - `sd.task.control.introduce` を受け取ったとき

##### JSON Schema
Body:
```json
{
    "type": "object",
    "required": [ "mesh_id", "name", "functions", "variables"],
    "properties": {
        "mesh_id": { "type": "string" },
        "name": { "type": "string" },
        "functions": { "type": "array", "items": {
            "type": "object",
            "properties": { "name": { "type": "string" }, "$comment": " 将来的には引数情報も追加" }
        }},
        "variables": { "type": "array", "items": {
            "type": "object",
            "properties": { "name": { "type": "string" }, "$comment": "将来的には型情報も追加" }
        }}
    }
}
```

##### JSON Example
Body:
```json
{
    "name": "mytask",
    "functions": [ { "name": "start" }, { "name": "stop" } ],
    "variables": [ { "name": "status" } ]
}
```

### sd.task.control.introduce
すべてのタスクに `sd.task.spec.{name}` を publish するように要求

##### 主な用途
- Sender: sd_taskprocess (SlowDash サーバー)
- Receiver(s): task process
- Timing: 
  - SlowDash サーバーの開始時
  - SlowDash サーバーが知らない Task の heartbeat を受け取ったとき

##### JSON Schema
Body:
```json
{
    "type": "object",
    "required": [],
    "properties": {}
}
```

## sd.rpc
Mesh の内部で RPC の実装に使用される．

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
トピック名 `sd.rpc_reply.{mesh_id}` は `sd.rpc` の `reply_to` で指定される．
ここでの `mesh_id` は，RPC リクエストを送った側の MeshID.


##### JSON Schema
Header: `sender`，`sender_id`，`message_id` 以外はリクエストメッセージと同内容．
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
- AsyncNATS, AsyncMQTT, AsyncRabbitMQ, AsyncRedis に on_reconnect を実装する
- Task 終了時の unregister
- RPC の引数型チェックと型変換
- RPC の呼び出し前に Last Heartbeat をチェック，なければ unregister

