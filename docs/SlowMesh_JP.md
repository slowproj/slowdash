---
title: SlowMesh と SlowTask
---

# 概要
SlowDash は，SlowDash サーバーの元で複数の SlowTask が協調して動作する分散並列システムです．
SlowMesh は，SlowDash サーバーおよび SlowTask 間のメッセージ交換通信基盤です．
SlowTask は，典型的には一つの Python スクリプトで，ユーザーによって書かれるものと，再利用可能なものを集めたライブラリに入っているものがあります．
SlowTask は SlowMesh の通信およびメッシュ上の各機能にアクセスするために，SlowPy ライブラリを使用します．

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
SlowDash サーバーと一緒に起動・終了することも，SlowDash サーバーとは独立に自分のタイミングで開始・終了することもできます．
SlowDash サーバーとは別の PC 上に走らせることもできます．

SlowTask には以下の機能が実装されています．

- 開始時・終了時や，一定時刻，一定時間間隔でのユーザー関数呼び出し
- SlowMesh による通信（関数のエクスポートやデータの送り出し）
- HTTP 経由での SlowDash サーバーとの通信（初期構成情報の取得など）



# SlowMesh
## 構成要素
### SlowPy Mesh ライブラリ
SlowTask スクリプトから使用されるライブラリです．

- Mesh (`slowpy.mesh.mesh.py`): SlowMesh 通信機能へのインターフェース
- Tasklet (`slowpy.mesh.tasklet.py`): Python スクリプトを SlowMesh 上の独立タスク (SlowTask) として実行するためのアダプタ
- MeshStdio (`slowpy.mesh.stdio.py`): Python スクリプトの標準入出力を Mesh の PubSub にリダイレクトするブリッジ
- MeshPakcet (`slowpy.mesh.packet.py`): SlowMesh で交換するメッセージのシリアライズ・デシリアライズ


### SlowDash Mesh サービス
SlowDash サーバー内で SlowMesh 関連のサービスを行うものです．

- Registry (Key-Value Store) サービス
- Pubsub Last-Value Cache (PubSub の全トピックを subscribe して受信データをレジストリの特殊パス（`$pubsub.{topic}`） に保持）
- WebMesh API: HTTP POST による publish と Server-Sent Events (SSE) による subscribe
- TODO: Control History (PubSub の`control.>` と `sd.rpc.>` トピックを subscribe して受信データをデータベースに保存）

### SlowMQ バックボーン
SlowDash 内蔵の PubSub ブローカーです．SlowDash のサーバープロセスに含まれているので，何も設定せずにそのまま使用できます．
WebSockets で実装されています．


## PubSub
### 使用例
典型的には，SlowMesh は後述の Tasklet によって構築されたものを使います．

##### Publish
```python
topic = 'data.store.temp0'
data = { 'temp0': { 't': t, 'x': temp0 } }
await tasklet.mesh.aio_publish(topic, data)
```

##### Subscribe
```python
@tasklet.mesh.on('data.store.>')  # メッセージ受信時のコールバックを指定
async def handle_data(headers, data):
    topic = headers.get('topic')
    ...
```

### バックボーン接続
SlowPy Mesh の PubSub は，SlowPy Control に実装されているメッセージングバックボーンへのインターフーェスに対する薄いラッパーです．
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

トピック名に `/`, `#`,`+`, `:` などを含めると，これらを特殊文字としているバックボーンを使用した場合に問題を引き起こします．
これらの文字の使用は避けた方がいいです．

なお，Mesh のコンストラクタオプションで，これらの文字割り当てを変えることができます．例えば，MQTT を中心に運用することが確定しているのであれば，SlowMesh においても MQTT と同じ特殊文字を割り当てておくことができます．

### MeshPacket
メッセージに対する Schema が定義されている一部のトピックに対しては，規定されたスキーマのデータを読み書きするための MeshPacket が利用できます．
MeshPacket 経由でメッセージ内容を読み書きすれば，ユーザーのスクリプトが Schema の詳細に依存せず，また，メッセージの構築や解読の手間が省けて便利です．

MeshPacket は，`slowpy/mesh/packet` に定義されています．
現時点で，以下の MeshPacket が利用可能です．

|トピック|MeshPacket コンストラクタ|
|---|----|
|`data.*.>` | `DataPacket(values, *, tag:str|None=None, timestamp:float|None=None)` |
|`control.>` | `ControlPacket()` TODO:未実装 |

#### データトピックの例
以下，`data.>` トピックに対する MeshPacket である mesh.DataPacket を例に説明します．このトピックに流すデータは [Data Model](DataModel.html) に説明されている SlowDash フォーマットを使用します．以下のように，ちょっと複雑です：
```python
{
    channel: {
       "start": t0,      # 時間原点 (optional)
       "t": time,        # TimeSeries データでは配列
       "x": value        # TimeSeries データでは配列
    }
    ...                  # 他のチャンネル
}
```

##### Publish
```python
from slowpy.mesh import DataPacket

topic = 'data.store'
temp0 = thermometer.ch(0).get()
await tasklet.mesh.aio_publish(topic, DataPacket(temp0, tag='temp0'))  # トピック名 data.store.temp0 で publish される
```
ここで，`DataPacket` のコンストラクタパラーメータは，`DataStore.append()` と同じです．
つまり，データストアに直接記録するのと，SlowMesh に publish するのは，ほぼ同じ書き方になります．


##### Subscribe
```python
from slowpy.mesh import DataPacket

@tasklet.mesh.on('data.>')  # メッセージ受信時のコールバックを指定
async def handle_data(data:DataPacket):
    t = data.timestamp
    for ch, value in data.values.items():
        ...
```

DataPacket には，コンストラクタのパラメータと同名のプロパティが定義されています．


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

- 書き込み (set)： `async def aio_set(self, key, value, *, cas_revision:int|None=None) -> int|None`
- 読み出し (get)： `async def aio_get(self, key:str, default:Any=None, *, with_meta:bool=False) -> Any`
- キー一覧 (keys)： `async def aio_keys(self, prefix:str='', limit:int|None=1000)->list[str]`
- 削除 (delete)： `async def aio_delete(self, key:str, *, cas_revision:int|None=None) -> bool`

**Key**:
階層区切り文字を除いて，Python や C++ などにおける識別子（変数名とか）と同じ感じの名前を使用してください．具体的には，英数字またはアンダースコアだけで構成され，かつ，最初の文字に数字は使用できません．

**Value**:
Value には，現時点では JSON にシリアライズできる値だけが使用できます．

**階層構造**:
Registry の内部は，階層構造を持たない単純な Key-Value Store です．Key は単なる文字列で，階層構造は SlowMesh では規定していません．ユーザが選んだ任意の階層区切り文字（ただし「識別子」として使えない文字のみ）を使うことを想定していますが，特に理由がなければ `/` による区切りを使用してください．
階層区切り文字にはアルファベット，数字，アンダースコアは使用できません．某 OS で行われているように，バックスラッシュなどの特殊文字を使用することも避けたほうが無難です．特に理由がなければ，`.`，`:`，`/` あたりから選ぶのがいいです．

```python
    registry = tasklet.mesh.registry
    
    await registry.aio_set('user', 'slowuser')
    await registry.aio_set('state/run/mode', 'physics')
    await registry.aio_set('state/run/number', 123)
    await registry.aio_set('state/run', 'running')    # 注：この例はあまり良くない．'state/run/status' に入れる方がいい

    print(await registry.aio_keys('state/run'))       # -->  ['state/run/mode', 'state/run/number', 'state/run']
    print(await registry.aio_get('state/run/mode'))   # -->  physics
    print(await registry.aio_get('state/run'))        # -->  running
    print(await registry.aio_get('state/run/'))       # -->  {'mode': 'physics', 'number': 123, '$value': 'running'}
    print(await registry.aio_get('/'))                # -->  {'user': 'slowuser', 'state': {'run': {'mode': 'physics', 'number': 123, '$value': 'running'}}}
```

最後の２つの例にあるように，`Registry.aio_get(key)` メソッドにおいて，key の最後の文字が英数字またはアンダースコアでない場合，その文字を階層区切り文字と解釈し，key の階層以下のすべての値を階層構造にまとめて，結果を dict として返します．

この例の `state/run` のように，ある key に値が割り当てられていて，かつ，その下に階層がある場合は，そのままでは自然な dict や JSON に変換できません（一つのノードが値と子ノードの両方をもつことができないため）．そのような場合，値は `$value` フィールドに格納されます．

レジストリの階層構造はどの区切り文字を使うかも含めてユーザーが自由に設計できますが，JSON として表現できる形に留める（子ノードがあるところに値を記録しない）のがおすすめです．上記の例では，`registry.set('state/run', 'running')` を`registry.set('state/run/status', 'running')` などとすれば，この問題を回避できます．

Registry では，他人が書いたものを意図せず上書きすることを防ぐため，Compare-And-Set (CAS) オプションを備えています．

- レジストリ値のメタデータには，書き込み回数を数える CAS Revision が割り当てられる
- `aio_set()` で CAS Revision はインクリメントされ，新しい CAS Revision が返される
- `aio_set()` で `cas_revision` オプションが None でない場合，オプションの値と保持されている値の CAS Revision と一致しないと，書き込みに失敗する
  - これにより，自分が設定した値を，他の誰かが書き換えた場合に，それを知らずに上書きすることを避けられる
- `aio_delete()` も同様．CAS Revision が一致しなければ削除に失敗する

`aio_get()` の `with_meta` オプションを `True` にすると，書き込み時刻や CAS Revision などを含んだ Meta Data が返されます：
```python
{
    "key": キー,
    "value": 値,
    "revision": CAS Revision,
    "updated": 最終書き込み時刻
}
```

レジストリに記録された値は，WebAPI からもアクセスできます．詳しくは，以下の HTTP API の章を参照してください．
```console
$ curl "http://localhost:18881/api/registry/value?key=state/run"
{"$value": "running", "mode": "physics", "number": 123}
```

また、データベース上のデータと同じ形式（同じ Web API と同じ戻り値フォーマット）で読むこともできます．
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


### PubSub Last-Value Cache
レジストリサービス（`sd-mesh-registry.py`）は，PubSub の全トピック（または指定されたトピック）を subscribe してその内容を保持することにより，PubSub Last-Value Cache を実装します．これにより，遅れて接続した Task が，それまでに Publish されたステータス情報などにアクセスできます．
TODO: さらに，この内容を定期的に保存することにより，SlowDash サーバークラッシュ後の復帰で，コンテキストを復元できます．

デフォルトでは，PubSub Cache は，レジストリの `$pubsub.{トピック名}`に保存されます．ここで，意図的にレジストリの推奨区切り文字とは異なる文字を使用しています．

例えば，レジストリの内容が以下のようになっていた場合，

```json
{
  "$pubsub.sd.task.spec.test_mesh_slowtask": {
    "mesh_id": "test_mesh_slowtask_vs13_158097_1",
    "name": "test_mesh_slowtask",
    "functions": [ { "name": "start" }, { "name": "display" } ],
    "variables": []
  },
  "$pubsub.sd.task.heartbeat.test_mesh_slowtask": {},
  "$pubsub.sd.task.spec.store": {
    "mesh_id": "store_vs13_214629_1",
    "name": "store",
    "functions": [],
    "variables": []
  },
  "$pubsub.sd.task.heartbeat.store": {},
  ...
```

- `$pubsub.sd.task.spec.test_mesh_slowtask.` を get すれば，そのタスクの Spec を一つの dict / JSON として取得できます．
- `$pubsub.sd.task.heartbeat.` を get すれば，すべてのタスクの Heartbeat を一つの dict / JSON として取得できます．

（サブブランチを含めて dict/JSON で取得するための，最後の `.` を忘れないように注意してください．）


## 標準入出力リダイレクト (MeshStdio)
MeshStdio を使うと，print() の出力などの標準出力が SlowMesh にも publish され，input() などの標準入力が subscribe からも取得されるようになります．
これにより，SlowTask の標準入出力を PubSub 経由で読み書きできるようになります．
WebUI に SlowTask のコンソールをもたせるなどの用途を想定しています．

```python
    from mesh.stdio import MeshStdio
    mesh_stdio = MeshStdio(self._mesh, topic_prefix='sd.task')
    
    await mesh_stdio.aio_start()
    # この間，print() が publish され，input() が subscribe から取得される
    await mesh_stdio.aio_stop()
    
```
`print()` または `sys.stdio` / `sys.stderr` に書かれたメッセージは，SlowMesh の指定トピックに publish され，かつ，ローカルの標準（エラー）出力にも書き出されます．同様に，`input()` または `stdin` からの取得リクエストは，SlowMesh への subscription またはローカルの標準入力の両方から読み出されます（先に来た方が受け取られる）．

PubSub に使われるトピック名は，`{prefix}.{stream}.{mesh_id}` です．例えば，Prefix が `sd.task` の場合の標準出力（stdout）のトピック名は，`sd.task.stdout.{mesh_id}` となります．

複数の MeshStdio を，それぞれ別々のスレッド上で作成し，start できます．その場合，入出力の振り分けは，スレッド ID により行われます．
（MeshStdio を start したスレッドで print() したものは，その MeshStdio インスタンスに渡される．）
SlowTask を動的ロードモジュールとして使った場合，複数の SlowTask が SlowDash サーバープロセスの中で動作しますが，その場合，各 SlowTask は別々のスレッドで動くので，それぞれが MeshStdio を持つことができます．

入出力チャンネルがスレッド ID に紐付けられるため，SlowTask の中で新たにスレッドを実行する場合には，そのスレッドに MeshStdio を明示的にアタッチし，スレッドの終了前に明示的にデタッチする必要があります．
```python
def thread_run():
    mesh_stdio.attach_current_thread()
    # ...
    mesh_stdio.detach_current_thread()
```
    
このように複数のスレッドにまたがって複数の MeshStdio が走っている場合には，ローカルの input() から来る入力をどのスレッドに渡すのかの不定性があります．
MeshStdio では，以下のルールで処理されます：

- 動作中の MeshStdio が一つしかない場合，ローカルの input() からの入力はそれに渡される
- ローカルの input() からの入力があった時点で，すでに input() 待ちをしているスレッドがある場合，それに入力が渡される．複数ある場合は，最後に input 待ちをしたスレッドに渡される．
- そうでない場合（複数の MeshStdio が走っているが，そのどれも input() 待ちをしていない場合），入力は破棄される

このルールは，ローカルの input() のみに適用され，宛先が明示されている SlowMesh の PubSub からの入力は，全て適切に割り振られることに注意してください．
ここで記述した振る舞いは，一つのプロセスの中で複数の MeshStdio があって，それらに対してローカルからの入力があった場合の動作です．

## HTTP ブリッジ (WebMesh)
WebMesh は，SlowDash サーバープロセスの一部で，SlowMesh に対する Publish / Subscribe を HTTP から行えるようにします．
Publish は通常の POST リクエスト，Subscribe は Server-Sent Events (SSE) を用いて実装されています．
現時点では，`data.*.` などの指定のトピックのみ subscribe 可能です．

### Subscribe
Subscribe するためには，まず `event/webmesh/attach` に SSE 接続をして，SSE 経由で配布される  `register` イベントからクライアントIDを取得します．

```javascript
    let sse = new EventSource('http://localhost:18881/event/webmesh/attach');
    let client_id = null;
    sse.addEventListener("register", (event) => {
        client_id = JSON.parse(event.data).client_id;
    }
```

そして，このクライアントIDを使用して，を subscribe します．
```javascript
    const subscribe_url = 'http://localhost:18881/api/webmesh/subscribe/data?client_id=' + client_id;
    const subscribe_message = {
       'channel': 'HV.ch0.V',
    };
    fetch(subscribe_url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
        body: JSON.stringify(subscribe_message),
    });
```

`data.*.>` トピックは `data` イベントとして，`sd.task.stdout.>` トピックは `stdout` イベントとして送信されます．
```javascript
    sse.addEventListener("data", (event) => {
        let data = JSON.parse(event.data);
    });
```

### Publish
Publish は，`api/webmesh/publish/{topic}` に POST するだけです．
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
SlowTask は SlowMesh の上で独立にかつ協調して動く実行単位（おおまかには，一つの Python スクリプト）です．
別プロセスとして動作し，SlowDash サーバーから管理することも，SlowDash サーバーとは独立に走らせることもできます．

## SlowTask の作成と実行
### スクリプト
Python スクリプトを SlowTask として使用するには，実行アダプタ Tasklet を組み込みます．
（あるいは，機能制限が付きますが，生の Python スクリプトをそのまま編集せずに SlowDash から実行する方法もあります．）

```python
from slowpy.mesh import Tasklet
tasklet = Tasklet()

...(本文)...

# もしスクリプトを単体実行したいなら
if __name__ == '__main__':
    tasklet.run(mesh_url='slowmq://localhost:18881')
```

SlowTask はシングルスレッドの非同期呼び出しで全体が並列に動くので，スクリプトの中で **`time.sleep()` を使うと全体が固まってしまいます**．
以下の `@tasklet.loop(interval)` を使ってループを書くことにより，明示的な sleep をしないのが想定です．
どうしても sleep をする場合は，`await asyncio.sleep()` または `await control_system.aio_sleep()` を使ってください．


### 実行
SlowTask のスクリプトファイルを，`slowtask-{名前}.py` という名前で SlowDash プロジェクトの `config` 以下に置くと，SlowDash サーバーに認識され，起動や停止を行えるようになります．

また，`SlowdashProject.yaml` ファイルに `task(s)` エントリを作って，`auto_start` を設定すると，SlowDash サーバー起動時に SlowTask も自動でスタートできます．
```yaml
  tasks:
    - name: {名前}
      auto_start: true
```

SlowTask を SlowDash サーバーから独立したプロセスとして実行するには，通常は `slowdash-task` コマンドを使います．
```console
$ slowdash-task  slowtask-mytask.py --mesh=slowmq://localhost:18881
```

もしスクリプト中で `if __name__ == '__main__': tasklet.run()` をしているなら，通常の Python スクリプトとしての実行もできます，
```console
$ slowdash-activate-venv
$ python slowtask-mytask.py
```

SlowDash サーバーからは，以下のような SlowTask の起動や停止を行えます：

- **Start**: SlowTask を子プロセスとして開始する．開始コマンドは，`SlowdashPoject.yaml` ファイルで指定できる．デフォルトは `slowdash-task` コマンドによるローカル実行．
- **Stop**: タスクに Heartbeat がある場合，SlowMesh 経由で タスクの `_sd_stop()` 関数を呼ぶ．
- **Kill**: タスクをサーバーから子プロセスとして実行した場合，子プロセスに KILL シグナルを送る．
- **Purge**: Heartbeat がなくなったタスクに代わって `sd.task.exit` を publish して，SlowMesh から抹消する．


独立に開始した SlowTask プロセスでも，SlowDash サーバーから停止操作 (stop) を行えます．ただし，サーバーからの強制終了 (kill) はできません．

SlowDash サーバーの中から起動された SlowTask プロセスは，デフォルトで，SlowDash プロセスが終了したときに自動で終了します．
（サーバーのクラッシュや強制終了でも，SlowTask プロセスは強制終了されます．）
独立に開始した SlowTask プロセスは，SlowDash サーバーが止まっても走り続け，次に同じ接続 URL の SlowDash サーバーが開始したときに，自動的に再接続されます．


## SlowTask の識別
各 SlowTask の実行インスタンス（走っているスクリプト）は，TaskName と MeshID の２つの名前を持ちます．

- TaskName: ユーザーによってつけられる名前（またはデフォルトでファイル名）．実行前に予測可能．同じ名前のタスクが複数あり得ることが想定されている．
- MeshID: システムによって実行時につけられる名前．実行時まで予測不能．同じ MeshID のタスクが同一メッシュ内に複数存在しないことが保証されている．

RPC 呼び出しなどは，呼び出し先の名前が事前に分かる TaskName を使います．もし同一の TaskName を持つタスクが複数存在する場合，全てのタスクに対して RPC 呼び出しが行われます．一方で，RPC 返信などは，呼び出し元の MeshID が使われ，呼び出したタスクだけに返信が戻るようになっています．
多くの場面で，ユーザースクリプトは TaskName を使い，内部では MeshID が使われています．

デフォルトでは，同じスクリプトを複数同時実行すると同じ TaskName になりますが，ユーザーは常に TaskName を明示的に指定することができます．TaskName の指定方法には，以下のようなものがあります．

- タスクスクリプトのファイル名（デフォルト）
- `Tasklet.run()` の `name` 引数
- `slowdash-task` コマンドの `--name` パラメータ
- `SlowdashProject.yaml` の `task` セクションの `name` パラメータ

TaskName には，英数字および `_` 以外の文字は使用できません．これらの文字が含まれる場合は，`_` に置き換えられます．

## SlowTask の機能
### Lifespan コールバック
tasklet が提供するデコレータにより，特定のタイミングや一定時間間隔に SlowTask 中の関数を呼び出すことができます．
同じデコレータを複数回使用することもできます．
特に，`@tasklet.loop(interval)` を小さい単位に複数使うことにより，スクリプトの中のループを避けることができて，スリープや終了処理などに伴う煩雑さを避けることができます．

- `@tasklet.initialize()`: スクリプト開始時に呼ばれる
- `@tasklet.finalize()`: スクリプト終了時に呼ばれる
- `@tasklet.once(delay:float=0)`: initialize から指定秒数後に呼ばれる
- `@tasklet.schedule(time:str, use_utc:bool=False)`: 指定時刻に繰り返し呼ばれる
- `@tasklet.loop(interval:float, ticks=None)`: 指定秒数間隔で繰り返し呼ばれる

#### 定時実行
`@tasklet.schedule(time)` デコレータにより，ユーザー関数を指定時刻に繰り返し呼び出すようにできます．

```python
@tasklet.schedule("08:00"):
def do_this_every_morning():
   # 毎朝８時に実行
```

引数の `time` は `HH:MM` 形式で指定します．`HH` および `MM` には，ワイルドカード `*` を指定でき，また，複数の時刻設定を `,` 区切りで並べることができます．夏時間への切替時に周期が変わらないようにするためには，`use_utc` を `True` にして，時刻を UTC で指定してください．

例）

- `@tasklet.schedule("08:00")`: 毎朝８時
- `@tasklet.schedule("00:00,08:00,16:00")`: 一日３回
- `@tasklet.schedule("*:00")`: 毎時０分
- `@tasklet.schedule("*:*")`: 毎分
- `@tasklet.schedule("*:00,*:20,*:40")`： 毎時３回
- `@tasklet.schedule("08:00", use_utc=True)`: 毎日 UTC ８時

`use_utc` が指定されない限り，時刻はローカル時刻ですが，Docker などのコンテナの中などで実行される場合は，ローカル時刻が UTC となっていることが多いことに注意してください．

#### ユーザループ
`@tasklet.loop(interval)` デコレータにより，ユーザー関数を指定周期で繰り返し呼び出すようにできます．

```python
@tasklet.loop(interval=1):
async def my_work():   # この関数は１秒（interval の値）ごとに呼ばれる
    #... do my work
```

さらに，`@tasklet.loop` に `ticks` を指定し，ユーザー関数に `tick` 引数を追加すると，`ticks` に指定した回数ごとに `tick` の値が True になります．
```python
@tasklet.loop(interval=1, ticks=10):
async def my_work(tick):
    # １秒毎にデータを読み，全てのデータをストリームに流す
    data = await HV.ch(0).aio_get()
    packet = DataPacket(data, tag='HV.ch00')
    
    await tasklet.mesh.aio_publish('data.stream.HV.ch00', packet)
    
    # データベースへの記録は１０回に１回
    if tick:
        await tasklet.mesh.aio_publish('data.store.HV.ch00', packet)
```

複数の tick 周期を指定することもできます．
```python
@tasklet.loop(interval=1, ticks={"transient_store":10, "store":60}):
async def my_work(tick):
    # １秒毎にデータを読み，全てのデータをストリームに流す
    data = await HV.ch(0).aio_get()
    packet = DataPacket(data, tag='HV.ch00')
    
    await tasklet.mesh.aio_publish('data.stream.HV.ch00', packet)
    
    # 一時データベース（短期間高密度）への記録は１０回に１回
    if tick.transient_store:
        await tasklet.mesh.aio_publish('data.transient_store.HV.ch00', packet)
        
    # 永続データベースへの記録は６０回に１回
    if tick.store:
        await tasklet.mesh.aio_publish('data.store.HV.ch00', packet)
```

繰り返しますが，ユーザー関数の中で `time.sleep()` は使わないでください．(`await control_system.aio_sleep()` は可）．
`@tasklet.loop()` を使うことにより，ほとんどの sleep をなくすことができるはずです．

### SlowMesh 機能

SlowTask は，内部に接続済 SlowMesh を保持していて，これを介して SlowMesh の通信機能を使用できます．

#### PubSub によるメッセージ交換
現時点では，データおよびヘッダに渡せる値は，JSON にシリアライズできるものに限られます．
<br>（TODO: バイナリをサポート）

- データを publish: `await tasklet.mesh.aio_publish(name:str, packet:XXXPacket)` (async メソッド)
- データに subscribe: `@tasklet.mesh.on(topic:str)` （デコレータ；本体関数で `packet:XXXPacket` を受け取る）

#### Registry (Key-Value Store) へのアクセス
- 書き込み (set)： `await tasklet.mesh.registry.aio_set(key, value, *, cas_revision:int|None=None) -> int|None`
- 読み出し (get)： `await tasklet.mesh.registry.aio_get(key:str, default:Any=None, *, with_meta:bool=False) -> Any`
- キー一覧 (keys)： `await tasklet.mesh.registry.aio_keys(prefix:str='', limit:int|None=1000)->list[str]`
- 削除 (delete)： `await tasklet.mesh.registry.aio_delete(key:str, *, cas_revision:int|None=None) -> bool`

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
必要に応じて，処理状況を逐次 publish するか，Registry に状態を記録するなどすれば，呼び出し側が状況を把握できます．
高信頼が必要な場合の高度な方法として，`sd.rpc.>` を subscribe して，システムが期待する状態に遷移するかを監視する SlowTask を走らせるという手もあります．

### config コンテンツの動的生成
`@content(name:str)` デコレータにより，通常は SlowDash プロジェクトの `config` 以下に置かれるファイルの内容を動的に生成することができます．以下の例では，ブラウザからは HTML ファイル `html-disk_usage.html` が `config` に存在するかのように見え，かつ，リロードする度に内容が変わるものです．ブラウザの HTML フォームで `On update: reload HTML` をチェックすることにより，データ更新のたびに新しい HTML が生成され表示されるようにすることができます．

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

`config/slowplot-XXX.json` も同じように生成できるので，HTML フォームと合わせて，SlowTask から，それを使うための完全なレイアウトを提供することができます．SlowTask 自体は普通の Python スクリプトなので，その中で例えば Jinja などのテンプレートエンジンを組み合わせて，動的な SlowDash レイアウトや HTML ページを作成することもできます．


### 標準入出力の SlowMesh PubSub へのリダイレクト
Tasklet のコンストラクタの `mesh_stdio` パラメータに `True` を渡す（デフォルト）と，ユーザースクリプト中の `print()` や `input()` などの標準入出力が PubSub にリダイレクトされます．TODO: これは，SlowDash サーバーを介して，Web Console へ接続されます．

- `print()` および `stdout`/`stderr` への `write()`: コンソール出力および `sd.task.stdout.{メッシュID}` へ publish
- `input()`: コンソール入力または `sd.task.stdin.{メッシュID}` からのメッセージから読み込み


### SlowDash Mesh サービスへのインターフェース
その他，SlowMesh の接続に必要な内部処理も行っています．

- Heartbeat の送り出し
- 仕様問い合わせ (`sd.task.introduce`) への応答
- 終了要求 `_sd_stop()` 関数のエクスポート
- 終了時の `sd.task.exit` への通知


## スクリプト中で明示的に Tasklet を使用しない場合
スクリプト中で明示的に Tasklet を使用しない場合でも，任意の Python スクリプトを SlowTask として使用することができます．この場合は，以下の機能のみが使用できます．

- SlowDash サーバーからの start/stop/kill コントロール
- すべての関数の export （他のタスクやブラウザからの呼び出し）
- 古いスタイルのコールバック：
  - `_initialize(params={})`: `@tasklet.initailze()` と同等
  - `_finalize()`: `@tasklet.finalize()` と同等
  - `_run()`: `@tasklet.once()` と同等
  - `_loop()`: `@tasklet.loop(interval=0)` と同等
  - `_get_html()`: `@tasklet.content('config/html-{name}.html')` と同等
  - `_get_layout()`: `@tasklet.content('config/slowplot-{name}.json')` と同等


# Example Projects
SlowTask の基本的な機能を使用する例が `ExampleProjects/Experimental/Mesh/` にあります．

- `slowtask-randomwalk.py` がダミーデータを生成して `data.store.HV.ch0.V` に publish
- `slowtask-store.py` が `data.store.>` を subscribe して，受け取ったデータを SlowPy DataStore に保存
- `slowtask-histogram.py` が `data.*.>` を subscribe して，受け取ったデータのヒストグラムを作成して `data.stream.histogram.{Channel}` に publish
- `slowtask-randomwalk.py` に対するブラウザから RPC 経由の set point 設定
- `slowtask-randomwalk.py` に対するブラウザから pubsub 経由の start/stop コントロール
- `slowtask-store.py` が `disk_usage` 変数をエクスポート，ブラウザがデータとして表示

### 実行
#### タスクをサーバーと一緒に自動開始・自動停止
`SlowdashProject.yaml` で，これらの SlowTask はサーバーと同時に自動スタートし，終了時に自動停止するように構成されています．
タスクが暴走した場合でも，サーバーはタスクをシグナルにより強制終了させることができます．
サーバーがクラッシュしたり，外部から即時強制終了 (SIGKILL) された場合でも，タスクは自動で同時終了します．

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

#### タスクを手動で開始，サーバーと一緒に終了
`auto_start` を `false` にするかコメントアウトすると，これらのタスクは自動では開始されません．
この場合，SlowDash のタスクコントロールパネルからスタートをクリックして開始できます．
コントロールパネルから開始されたタスクは，サーバー終了時に自動で終了します．
また，タスクが暴走した場合でも，サーバーはシグナルを使って強制終了させることができます．

#### タスクをサーバーとは独立に実行
自動開始が設定されていない，またはそもそもタスクエントリが書かれていないタスクは，サーバーと独立に実行できます．
この場合，この SlowTask を実行するためには，新しいターミナルを開いて `slowdash-task` コマンドを使用してください．
タスクが SlowMesh にアクセスできる限り，タスクプロセスを別PCや別コンテナ上で実行しても構いません．
SlowDash サーバープロセスを走らせたままタスクプロセスの停止・再実行をしても大丈夫なはずです．
また，タスクプロセスを走らせたまま SlowDash サーバーの停止・再実行をしても自動再接続をするはずです．
```console
$ cd PATH/TO/PROJECT
$ slowdash-task config/slowtask-store.py --mesh=slowmq://localhost:18881
```
この場合でも，SlowDash のタスクコントロールパネルから，タスクの「終了要求」を出すことができます．
もしタスクが Tasklet で実装されていて，暴走していなければ，通常はこれできれいに終了します．
サーバーと独立に開始されたタスクは，サーバーからのシグナルによる強制終了はできません．


### 構成要素

#### 読み出しタスク（`slowtask-randomwalk.py`）
RandomWalk タスクでは，tasklet のループコールバックで 1 秒ごとにダミーデータを読み出し，それを `data.store.HV.ch0.V` トピックに publish します．
```python
@tasklet.loop(interval=1.0)
def loop():
    if not device.is_running:
        return
    data = device.ch(0).get()
    tasklet.mesh.publish('data.store', DataPacket(data, tag='HV.ch0.V'))
```

読み出しのスタート・ストップは PubSub の `control.start` および `control.stop` によりコントロールされます．
また，スタート・ストップの際には，動作状態をレジストリに記録しています．
```python
@tasklet.mesh.on('control.start')
async def start(params):
    device.is_running = True
    await tasklet.mesh.registry.aio_set('setup/run/status', 'running')

@tasklet.mesh.on('control.stop')
async def stop(params):
    device.is_running = False
    await tasklet.mesh.registry.aio_set('setup/run/status', 'idle')
```

RandomWalk 仮想デバイスのセットポイントは， （機能デモのために）export した RPC で設定されます．実際には，Start/Stop と同様に PubSub を使用しても構いません．
```python
@tasklet.mesh.export
def set_value(value:float):
    device.ch(0).set(value)
```

#### データ保存タスク（`slowtask-store.py`）
RandomWalk タスク が publish したデータは，store タスクによって subscribe され，データベースに記録されます．
```python
@tasklet.mesh.on('data.store.>')
def store(data:DataPacket):
    datastore.append(data.values, tag=data.tag, timestamp=data.timestamp)
```

複数のプロセスがデータを publish しても，全てのデータはこの一箇所でデータベースに記録されるので，例えば SQLite のようなトランザクションを持っていないデータベースに書く場合でも，競合を避けることができます．
また，データフォーマット（テーブルスキーマ）の記述も一箇所にまとめられます．

##### 追加その１
この例の Store タスクは，ディスク容量を返す ControlNode のインスタンス `disk_usage` をエクスポートしていて，外部からの「データ要求」でそれを返します．
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

SlowTask の HTTP API により，タスクから export された変数は，データベースに保存されているデータと同様にアクセスできます．（タイムスタンプが「現時刻」のデータが一点だけ保存されているように見える．）

publish が基本的にデータ生成元からの push なのに対して，ControlNode の export は，外部からの pull 要求でデータを返すインターフェースです．「必要なときに最新値を得る」用途に向いています．

##### 追加その２
この例の Store タスクは，通常は SlowDash プロジェクトの `config` 以下に置かれるファイルを動的に生成する例も含まれています．
`@content(name)` で，コンテンツ名と，それを生成する関数を結びつけています．

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

ブラウザの HTML フォームで "On update: reload HTML" をチェックすると，データ更新のたびにこのコンテンツ生成関数が呼ばれるので，データを含んだ HTML ページを動的に生成することができます．

#### データ解析タスク（`slowtask-histogram.py`）
RandomWalk タスク が publish したデータは，Histogram タスクによって subscribe され，解析されます．
解析結果のヒストグラムは，`data.stream.histogram.{Channel}` に publish されます．

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
データ頻度に関係なく一定周期でヒストグラムを publish するために，到着データ解析とヒストグラムの publish は別のコールバックになっています．
データ保存タスクは `data.store.>` にしか subscribe していないので，`data.stream` に publish したこのデータは保存されず，オンラインディスプレイのみに表示されます．

`is_running` ステータスは，start/stop の subscribe に加えて，RandomWalk がレジストリにセットしたものを initialize で読むことにとより，解析プロセスを停止・再開した場合でも正しくステータスを処理できるようになっています．
```python
@tasklet.initialize()
async def initialize():
    global is_running
    is_running = (await tasklet.mesh.registry.aio_get('setup/run/status', 'dead') == 'running')

@tasklet.mesh.on('control.start')
async def start():
    global is_running
    is_running = True

@tasklet.mesh.on('control.stop')
async def stop():
    global is_running
    is_running = False
```


#### Web フォーム（`html-startstop.html`）
ブラウザの Web フォームからスタート・ストップの publish やセットポイント設定の RPC を行っています．
```html
<form>
  <b>Device Controls</b> (Function Call)<br>
  Set Point: <input type="number" name="value" value="10">
  <input type="submit" name="randomwalk.set_value()" value="Set">
  <p>  
  <b>Run Controls</b> (Publish)<br>
  <input type="submit" name="publish control.start()" value="Start">
  <input type="submit" name="publish control.stop()" value="Stop">
</form>
```
ボタン（`<input type="submit">`）の `name` 属性でボタンをクリックしたときの動作を記述しています．

- `randomwalk.set_value()`: randomwalk タスクの `set_value()` 関数の遠隔呼び出しをする．渡される関数の引数は，ここに書かれた引数リスト（この例では空）と他の `<input>` 要素の name-value 対を合わせたものになる．
- `publish control.start()`: `control.start` トピックに publish する．publish データは引数リスト（この例では空）と他の `<input>` 要素の name-value 対を JSON にしたものになる．

#### SlowPlot レイアウト （`slowplot-control.json`）
以下のものを並べたものです．

- 読み出しタスクのコントロールのための Web フォーム (`html-startstop.html`）
- Store タスクによりデータベースに保存されたデータのプロット (`HV.ch0.V` の時系列プロット）
- Histogram タスクによりストリーミングされるオンライン解析結果の表示(`data.stream.histogram.HV.ch0.V` プロット)
- RandomWalk タスクが publish したデータをストリーミングチャンネル経由で直接受信した値の表示(`HV.ch0.V` の Single Value Display)
- Store タスクが export した disk_usage の表示 (`store.data_usage` データチャンネル)
- Store タスクが動的生成した HTML コンテンツ (disk usage テーブル） の表示 (動的生成 `config/html-disk_usage.html` ファイルコンテンツ）
- レジストリに保持されている値の表示
  - `randomwalk/run/status` の値を Single Scalar として表示 （`@registry:randomwalk/run/status` データチャンネル）
  - `randomwalk` 以下全体を Tree として表示 (`@registry:randomwalk/` データチャンネル)
  - PubSub Last-Value Cache 全体を Tree として表示 （`@registry:$pubsub.` データチャンネル）


# HTTP API
## SlowTask

SlowTask への HTTP API は Slowlette を経由して `sd_task.py` コンポーネントにより実装されています．

### Task コントロール
#### GET `api/task/catalog`
タスクのコンフィギュレーションやスクリプトファイルなどから，タスク設定の一覧を返す．

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
Task Spec を含む全ての実行中タスクのステータス一覧を返す．

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
        "stdin": [ "sd.task.stdin.store_vp13_17769_1" ],
        "stdout": [ "sd.task.stdout.store_vp13_17769_1" ],
        "stderr": [ "sd.task.stdout.store_vp13_17769_1" ]
      }
    }
  },
  {
    "name": "randomwalk",
    ...
```


#### POST `api/task/control/{taskname}`
指定したタスクの開始，停止，強制終了を行う

- Body は `action` フィールドのみ．`action` の値は，`start` / `stop` / `kill` のいずれか．
  - `start` は，catalog に `command` がある場合のみ．`Popen()` により子プロセスとして実行される．
  - `stop` は，SlowMesh 上に Heartbeat がある場合のみ．SlowMesh RPC で Tasklet の `_sd_stop()` 関数が呼ばれる．
  - `kill` は，status に `pid` がある場合のみ（外部で起動された SlowTask は kill できない）．SIGKILL が送られる．
    - `command` が `ssh` でも，RetainerAutocide が設定されている場合 (`slowdash-task` のデフォルト)，ssh の子プロセスとしての SlowTask も kill されるはず．

### 一般コントロールインターフェース
#### POST `api/control`
Mesh メッシュリクエスト

- Body は HTML の Form 入力値の JSON ドキュメント（フォーム中の `<input>` の `name` と `value` を集めた object）
- `type="submit"` の `<input>` エレメントの `name` をリクエストと解釈する

##### RPC Call Request (旧形式の slowtask function call と互換)
- Syntax: `タスク名.関数名(固定パラメータリスト)`
- Example: `<input type="submit" name="run_controller.start(run_mode='normal')">`
- Form 中の `type="submit"` 以外の `<input>` 要素の `name` と `value` に固定パラメータを追加したものが RPC の引数に渡される．
- RPC のシグニチャを見て，必要なパラメータのみを選んで，型チェック・型変換もする
- レスポンス：
  - 成功： 200, `{ "status": "ok", "return_value": return_value }`
  - RPC エラー (呼び出し先例外)： 200, `{ "status": "error", "message": error_message }`
  - RPC キャンセル (呼び出し先 Async-Task Cancelled)： 200, `{ "status": "cancelled" }`
  - その他エラー: 400 番台のエラーレスポンス

##### Publish Request
- Syntax: `publish トピック名(固定パラメータリスト)`
- Example: `<input type="submit" name="publish my_setup.start(run_mode='normal')">`
- Form 中の `type="submit"` 以外の `<input>` 要素の `name` と `value` に固定パラメータを追加した Key-Value Pairs の JSON object が publish される．
- レスポンス：
  - 成功： 200, `{ "status": "ok" }`
  - エラー: 400 番台のエラーレスポンス


### 一般データインターフェース

#### GET `api/channels`
Task が export している変数の名前をデータベース中のデータと同じ形式でリストして返す

#### GET `api/data/{channels}?length={length}&to={to}`
Task が export している変数の値をデータベース中のデータと同じ形式で返す

- length と to で指定されるクエリ期間が現在時刻を含んでいる場合のみ値を返す（典型的には `to` が `0` のクエリ）


### 一般 config インターフェース

#### GET `api/config/contentlist`
Task が提供している contents のうち，名前が `config/` で始まるものについて，SlowDash Project の `config` 以下にあるファイルと同様のリストを生成して返す

#### GET `api/config/content/{content_name}`
Task が提供している contents のうち，名前が `config/` で始まるものについて，その内容を返す


## Registry (Key-Value Store)

Registry への HTTP API は Slowlette を経由して `sd_mesh_registry.py` コンポーネントにより実装されています．

### Registry アクセス

#### GET `api/registry/value?key={key}`
Registry に保持されている値を返す（`with_meta=true` でメタデータを含む JSON ドキュメント）

#### GET `api/registry/keys?prefix={prefix}&limit={limit}`
Registry に保持されているキーのリストを返す

### 一般データインターフェース

#### GET `api/data/{channels}?length={length}&to={to}`
Registry に保持されているキーの値をデータとして返す（データベースからのデータと同形式）．

- channel が `@registry:{key}` となっているものが対象
- TODO: レジストリメタデータの [updated, now()] とデータクエリ期間が重なるものが対象


## WebMesh
WebMesh は，SlowMesh の PubSub を HTTP 経由で行えるようにするブリッジです．Slowlette を経由して `sd_webmesh.py` コンポーネントにより実装されています．

### PubSub

#### EventSource(`event/webmesh/attach`)
SSE 接続チャンネルを作成する．

  - `register` イベント： サーバーが ClientID を配布
  - `data` イベント： `data.*.>` トピックのメッセージ
  - `stdout` イベント： `sd.task.stdout.>` トピックのメッセージ

#### POST `api/webmesh/subscribe/data?client_id={client_id}`
データストリーミングのために Subscribe するチャンネルを指定する．複数回呼び出しが可能．
POST する body に JSON で `channel` を指定．

#### POST `api/webmesh/unsubscribe`
すべての subscribe を取り消す

#### POST `api/webmesh/publish/{topic}`
SlowMesh へ publish する．

### 一般データインターフェース

#### GET `api/channels`
`data.*` トピックに流れているデータのチャンネル一覧を返す



# RPC サービス
## Registry (Key-Value Store)
- モジュール名： `sd_mesh_registry`
- エクスポート関数：
  - 書き込み： `async def aio_set(self, key, value, *, cas_revision:int|None=None) -> int|None`
  - 読み出し： `async def aio_get(self, key:str, default:Any=None, *, with_meta:bool=False) -> Any`
  - キー一覧： `async def aio_keys(self, prefix:str='', limit:int|None=1000)->list[str]`
  - 削除： `async def aio_delete(self, key:str, *, cas_revision:int|None=None) -> bool`


## Task RPC
- モジュール名： `{task_name}` (デフォルトで，スクリプトファイル名が `slowtask-{task_name}.py`)
- エクスポート関数：
  - Task Script 中で `@export` したもの
  - `_sd_stop()`: 停止リクエスト
  - `_sd_get_content(name:str)`: Task Contents を取得


# 予約済み Registry
## SlowDash サーバー情報
- `$server.url`

## PubSub Last-Value Cache
- `$pubsub.{トピック}`



# PubSub トピック構成
## data
### トピック名構成
- `data.store.{チャンネル名}`: 永続データ
- `data.stream.{チャンネル名}`: モニタデータ

### MeshPacket
`DataPacket(values, *, tag:str|None=None, timestamp:float|None=None)`

- `DataStore.append()` と同じ引数

### フォーマット
SlowDash 標準データフォーマット


## sd.task
- すべての SlowTask Process は `sd.task.control.>` を subscribe すること．

### sd.task.heartbeat.{task_name}.{mesh_id}
Task の生存信号．Body に記録されるのは expire (= time-of-heartbeat + heartbeat-interval)．Expire が現在時刻よりも古ければ，Heartbeat が出ていないとみなす．

##### 主な用途
- Sender(s): task process
- Receiver(s): sd_task (SlowDash サーバー)，モニタサービス
- Timing:
  - 指定時間間隔（`Tasklet._heartbeat_interval`，１０秒）
  - Tasklet のメインループから送出（コルーチンやスレッドではない；必ずメインと一緒に停止する）

##### 第２用途
- サーバーは知らないタスクから Heartbeat を受け取った場合，PubSub に `sd.task.control.introduce` を publish する

##### 第３用途
- サーバークラッシュなどによる PubSub の接続断後の再接続は publish にトリガされるので，heartbeat 送り出しが接続断後の reconnect retry になる
- Reconnect により，`sd.task.spec` 再送などもトリガされる
- サーバー復帰後のシステム再開は，heartbeat interval 程度遅れることになる

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
タスクが外部公開している関数と変数の一覧

##### 主な用途
- Sender(s): task process
- Receiver(s): sd_task (SlowDash サーバー)
- Timing:
  - タスクが開始したとき
  - `sd.task.control.introduce` を受け取ったとき

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
                "type": { "type": "string", "enum": [ "control_node" ], "$comment": " 将来的には dataclass type などを追加するかも．readonly とかも．" },
                "data_type": { "type": "string", "enum": [ "numeric", "string", "tree", "table", "histogram", "graph" ] },
                "probe_value": {}
        },
        "stdio": {
            "type": "object",
            "properties": {
                "stdout": { "type": "string", "$comment": "stdout が publish されるトピック名" }, 
                "stderr": { "type": "string", "$comment": "stderr が publish されるトピック名" }, 
                "stdin": { "type": "string", "$comment": "subscribe の受信が stdin へ送られるトピック名" }
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
タスクの終了を通知

##### 主な用途
- Sender: task process
- Receiver(s): sd_task (SlowDash サーバー)，モニタサービス
- Timing: 
  - Task 終了時

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
すべてのタスクに `sd.task.spec.{task_name}.{mesh_id}` を publish するように要求

##### 主な用途
- Sender: sd_task (SlowDash サーバー)
- Receiver(s): task process
- Timing: 
  - SlowDash サーバーの開始時
  - SlowDash サーバーが知らないタスクの heartbeat を受け取ったとき

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
タスクの外部監視による実行状態の変化を通知

##### 主な用途
- Sender(s): sd_task (SlowDash サーバー) / slowdash-task （スクリプトローダ）
- Receiver(s): sd_webmesh 経由のタスクモニタなど
- Timing:
  - SlowTask ローダーがスクリプトをロードしたとき (`script loaded`)
  - SlowTask ローダーがスクリプトのロードに失敗したとき (`script loading failed`)
  - サーバーが task spec を受け取ったとき (`registered`)
  - サーバーが task exit を受け取ったとき (`completed` / `died in error`)
  - サーバーの監視で heatbeat が失われたとき (`heartbeat stopped`)
  - サーバーの監視で heatbeat が復活したとき (`heartbeat recovered`)

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
タスクの stdout/stderr へ出力のリダイレクト

##### 主な用途
- Sender: task process
- Receiver(s): sd_webmesh 経由のタスクモニタや Web Console など

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
タスクの input() 入力への PubSub からの注入

##### 主な用途
- Sender(s): sd_webmesh 経由のタスクモニタや Web Console など
- Receiver: task process

##### JSON Schema
Body:
```json
{
    "type": "object",
    "properties": {
        "text": { "type": "string" }
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
- Tasklet Initialize params
- AsyncNATS, AsyncMQTT, AsyncRabbitMQ, AsyncRedis に on_reconnect を実装する
- レジストリを SlowTask でも動かせるようにする
- MyMesh: SlowTask を SlowMesh なしで動かした場合に使う．コンソールから接続し，!!! から始まる行を拾う
- Task RPC Proxy
- dataclass の export
