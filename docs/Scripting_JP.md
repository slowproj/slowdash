---
title: Scripting
---

# 概要

SlowDash は，Web GUI と Python Scripting のハイブリッドシステムです．
Web GUI の表示部品の裏側に，その動作を記述する Python のコードを付加してシステムを構築します．

ここでユーザーが作成する Python スクリプトはごく標準の Python で，既存のシステムや任意の外部ライブラリを使用することができます．
スクリプト中の関数は Web GUI にバインドされますが，バインドは GUI の側で指定する（アクションの際に呼び出すユーザースクリプト中の関数名を指定する）ので，ユーザースクリプトの側では SlowDash のフレームワークやライブラリを全く使わないこともできます．

一方で，SlowDash の機能をより積極的に使うこともできます．
多くの場合，ユーザー関数に一行のデコレーターを付加するだけで，並行・並列実行制御などを含むより高度なバインディングを使用でき，また繰り返し実行や開始時実行などを簡単に行うことができます．

SlowDash は，デバイスアクセスなど，ユーザースクリプト中で頻繁に使用する機能を実装したライブラリ SlowPy を提供しています．
SlowPy の使用は任意ですが，使用すると多くのことが簡単にできるようになります．
また，SlowPy 自体は，SlowDash サーバーなしで使用することができ，SlowPy を使ったユーザースクリプトも，SlowMesh の通信を使わない限り，SlowDash サーバーなしで単体で実行できます．

SlowDash システムの一部として動作するユーザースクリプトを SlowTask と呼びます．SlowTask は通常，独立したプロセスとして実行されます．
SlowTask は，SlowDash サーバーの開始と一緒に自動起動することも，Docker Compose などでサーバーとは独立に開始・停止することもできます．

SlowPy を使用して SlowDash のフレームワークの中でユーザースクリプトを動作させれば，複数の SlowTask の間でのメッセージ通信や遠隔関数呼び出し，パラメータ共有などを通して，協調動作をさせることができます (SlowMesh)．
ある程度以上の規模のシステムでは，複数の SlowTask が並列に動作するのが普通で，さらに SlowTask を，スクリプトの変更なしに，ネットワーク上に分散配置することもできます．
SlowDash の分散処理機能を使わず，Docker Swarm や Kubernetes などの別のシステムで SlowTask プロセスを管理しても，全く同じように動作します．
データベース記録など，一部の SlowTask スクリプトは汎用部品として SlowDash の配布パッケージに含まれており (SlowTools)，それらを組み合わせてシステム構築を行うこともできます．

SlowMesh 上で複数の SlowTask を走らせる例が [Quick Tour](QuickTour.html) にあり，使用後にきれいに捨てられる環境で試してみることができます．
この章では，SlowPy を使って SlowTask スクリプトを作成しシステムを構築する方法の詳細を説明します．

# SlowPy ライブラリ
## 構成
SlowPy ライブラリは SlowDash の `slowdash/lib/slowpy` にあり，SlowDash サーバーおよび Web GUI (`slowdash/app` 以下)とは分離されています．
SlowPy パッケージは以下の複数のサブパッケージから構成されています．
`import slowpy` で一括 import できますが，使用する際は `slowpy.control.XXX` のように，サブパッケージ名を付けて書く必要があります．
あるいは，`import slowpy.control` や `from slowpy.control import XXX` のようにしても構いません．

| 名前 | 役割 | 外部依存 |
|---|---|---|
| control | デバイスや外部制御システムのコントロール | ベンダ提供ライブラリ（もしあれば） |
| (トップレベル) | ヒストグラムなどのデータ解析部品 | - |
| store   | データ記録 | 使用するデータベースシステム |
| mesh    | SlowMesh 通信 | SlowDash サーバー |

ヒストグラムなどの解析部品は `slowpy` のトップレベルにあり，`slowpy.Histogram` のように使用します．

ユーザースクリプト中で `slowpy.mesh` を使用して実際に通信している場合のみ，実行に SlowDash サーバーが必要です．
それ以外の場合，作成したスクリプトは SlowDash とは独立に単体実行ができます．
これは，スクリプトの開発に便利です．
SlowPy ライブラリは，SlowDash の標準インストールでは，venv の中にインストールされるので，単体実行の場合は，使用する前に venv をアクティベートしてください．
これは SlowDash サーバーから SlowTask として実行する場合には必要ありません．
```console
$ slowdash-activate-venv    # （または，source PATH/TO/SLOWDASH/venv/bin/activate）
```

SlowDash のリリースに対応した SlowPy は pip でインストールすることもできます．
解析だけをする PC で SlowPy を使用する場合に便利かもしれません．
SlowDash にリリースタグをつけたときだけ更新されるので，pip 上の SlowPy は古くなっている場合がある点に注意してください．
```console
$ pip install slowpy
```

## 簡単な例
#### イーサネット接続の電圧計から SCPI コマンドで測定値を読む
```python
from slowpy.control import control_system as ctrl

# Create a control node for SCPI command "MEAS:VOLT:DC" on a device at 192.168.1.43
V = ctrl.ethernet('192.168.1.43', 5025).scpi().command('MEAS:VOLT:DC')

while True:
  # Read a value from the control node using SCPI command "MEAS:VOLT:DC?"
  value = V.get()
  ...
```

#### データを PostgreSQL データベースに記録する
```python
from slowpy.store import DataStore_PostgreSQL

datastore = DataStore_PostgreSQL('postgresql://postgres:postgres@localhost:5432/SlowTestData', table="SlowData")

while True:
    value = ...
    datastore.append(value, tag="voltmeter")
```

#### SlowDash の Web GUI から関数を呼び出す
スクリプト `config/slowtask-test.py` 中の出力電圧設定関数 `set_Vout()`:
```python
from slowpy.control import control_system as ctrl
Vout = ctrl.ethernet('192.168.1.43', 5025).scpi(append_opc=True).command('VOLT')

def set_Vout(value:float):
    Vout.set(value)
```
Web GUI のユーザー作成 HTML (`config/html-test.html`):
```html
<form>
  Voltage output: <input name="value">
  <button name="test.set_Vout()">Set</button>
</form>
```
ブラウザ上で `Set` ボタンをクリックすると，`<input name="value">` フィールドに設定された値が float に変換されて，それを引数に `set_Vout(value)` が呼ばれます．

##### 少しだけ改良 その１
関数は通常の関数と async 関数のどちらも使用できます．async にすると他の処理と並行に実行され，全体の応答性が良くなります．
```python
async def set_Vout(value:float):
    await Vout.aio_set(value)
```

##### 少しだけ改良 その２
SlowPy において SlowTask をコントロールする `Tasklet` を使用すると，ブラウザから呼び出す関数を明示的に指定することができます．
```python
from slowpy.mesh import Tasklet
tasklet = Tasklet()

@tasklet.mesh.export()
async def set_Vout(value:float):
    await Vout.aio_set(value)
```

#### １秒ごとにデータを読み出し，ブラウザにストリーミングする
```python
from slowpy.mesh import Tasklet
tasklet = Tasklet()

from slowpy.control import control_system as ctrl

device = ctrl.ethernet('192.168.1.43', 5025).scpi()
V = device.command('MEAS:VOLT:DC')
A = device.command('MEAS:CURR:DC')

@tasklet.loop(interval=1.0)
def loop():
    ctrl.stream('voltage', V.get())
    ctrl.stream('current', A.get())
```

##### 少しだけ改良
上記同様，async を使用すると性能が良くなります．
```python
@tasklet.loop(interval=1.0)
async def loop():
    await ctrl.aio_stream('voltage', await V.aio_get())
    await ctrl.aio_stream('current', await A.aio_get())
```

## コントロール
### ノードツリー構造
SlowPy は，外部のソフトウェアシステムやハードウェアデバイスに接続するための統一インターフェースを提供します．
全てのものは一つの「コントロールツリー」にマップされ，ツリーの各ノードは `set()` と `get()` のメソッドを持ちます．
ツリーはシステムの論理構造を表しています．
例えば，イーサネット経由で接続された電源装置に対する SCPI コマンド `VOLT` は，`ControlSystem.ethernet(host, port).scpi().command('VOLT')` のように指定され，このノードに対して `set(value)` を呼ぶと，デバイスに SCPI コマンド `VOLT value` が送られます．
`get()` メソッドは読み出し操作を行い，値を返します．

プラグインモジュールにより，コントロールツリーに動的に枝を追加することができます．
例えば，Redis プラグインは `redis()` ノードと，ハッシュや JSON，時系列などの Redis が提供する機能に対応するいくつかの下位の枝を追加します．
プラグインは，必ずしもルートの ControlSystem ではなく，任意のノードにロードされます．
例えば，イーサネットを使用するプラグインはイーサネットノードにロードされてその下に枝を作成し，プラグインはイーサネットノードが提供する `set()`（送信）や `get()`（受信）などの機能を利用することができます．

#### 例
以下は SlowPy Controls の使用例です．この例では，イーサネット経由で SCPI コマンドを受け付ける電源装置を使用しています．

```python
from slowpy.control import control_system as ctrl

# Create a control node for SCPI command "VOLT" (output) and "MEAS:VOLT:DC" (readback) on a device at 192.168.1.43
device = ctrl.ethernet('192.168.1.43', 5025)
Vout = device.scpi(append_opc=True).command('VOLT')
V = device.scpi().command('MEAS:VOLT:DC')

# Write a value to the control node: this will issue SCPI command "VOLT 10;*OPC?"
Vout.set(10)

while True:
  # Read a value from the control node using SCPI command "MEAS:VOLT:DC?"
  value = V.get()
  ...
```
通常は，この例のように `slowpy.control` からインスタンス `control_system` を直接 import するところから始めます．
（`ControlSystem` クラスを import して，自分でインスタンスを作成しても構いません．）

`ControlSystem` にはすでに `Ethernet` プラグインが含まれていますが，もし含まれていなかった場合，プラグインをロードするコードは以下のようになります．
```python
ctrl.import_control_module('Ethernet')
```
これにより，検索ディレクトリ（カレントディレクトリと SlowPy のディレクトリ）から `control_Ethernet.py` という名前のファイルが探されてロードされ，プラグインをロードしたノードのクラス（この場合は ControlSystem）に `ethernet()` メソッドが追加されます．
`import_control_module()` はノード自身を返すので，`ctrl.import_control_module('DummyDevice').randomwalk_device()` のように続けて書くこともできます．
Ethernet プラグインにはすでに SCPI と Telnet の枝が含まれています．それ以外の特定のプロトコルを使う場合は，そのためのプラグインをイーサネットノードにロードします．

各ノードのコンストラクタはパラメータを取ります．
この例では，イーサネットとの間でデータの送受信をするイーサネットノードは，ホスト名（IP アドレス）とポート番号をパラメータに取ります．
特定の SCPI コマンドに結びつけられた SCPI コマンドノードは，SCPI コマンドをパラメータに取り，オプションで書き込み時のコマンドを変更する `set_format` を指定できます．
（`.scpi().command(CMD)` に対して，デフォルトで書き込み時に送られるコマンドは `CMD value`，読み出し時は `CMD?` です．）

SlowPy は，全ての SCPI コマンドに応答があることを想定しています．
多くの場合，書き込み操作ではコマンドの完了を待つ必要もあります．
デバイスの実際のコマンドの振る舞いによらずにこれを実現する方法として，例のように，コマンドに `*OPC?` を付加するという手があります．
`scpi(append_opc=True)` とすると，そのノード以下の全ての `set()` に `*OPC?` が付加されます．（もともと応答のある `get()` には付加されません．）
コマンドごとに切り替えたい場合は，`command('OUTP ON;*OPC?')` のように，自分でコマンドに `*OPC?` を付加しても構いません．

コントロールノードのオブジェクトを取得したら，`node.set(value)` で値を書き込み，`value = node.get()` で値を読み出すことができます．

コネクションノード（`ethernet()` など）を複数回呼んだときに，新しいコネクションが作られるか同じものが再利用されるかは，ノードの種類やパラメータによります．
通常は，例のように，デバイスレベルのノードを一度作成して変数に保存しておくと便利です．

### 非同期 (Async) インターフェース
SlowDash がユーザースクリプトを SlowTask として実行する場合，明示的に指定しない限りはシングルスレッドの async システムとして動作し，全体が async を使用して並行処理をしています．
このため，ユーザー関数の実行に時間がかかると全体が固まってしまいます．
ユーザースクリプトの関数も async として実装し，その中で時間のかかる処理には，SlowPy ノードの async 版のメソッドを `await` 付きで呼ぶことが推奨されています．
```python
async def set_Vout(value:float):
    await Vout.aio_set(value)
```

この目的のため，SlowPy のノードでは，ほとんどすべてのメソッドに async 版が用意されています．
これらは，通常関数(`set()`/`get()` など)の名前にプレフィックス `aio_` を付けた名前になります(`aio_set()`/`aio_get()` など)．

多くの SlowPy デバイスで `set()`/`get()` と `aio_set()`/`aio_get()` の両方が実装されていますが，実際にどちらが使用できるかはデバイスによります．
`set()` だけが実装されていて `aio_set()` がない場合，`await aio_set()` 呼び出しは `asyncio.to_thread()` を経由するか（スレッドセーフが明示的に宣言されている場合），そのまま `set()` にフォールバックします（スタベーションの可能性あり）．
ノードがスレッドセーフであるかどうかは，`ControlNode` ベースクラスの `_is_thread_safe` メンバ変数に格納されています．

`sleep()` や `wait()` などのブロッキングする関数にも `aio_sleep()` や `aio_wait()` などの async 版があります．
SlowTask の中では，`time.sleep()` や `ctrl.sleep()` の代わりに `await ctrl.aio_sleep()` を使用してください．

### コントロールノードのスレッドと非同期タスク
コントロールノードの中には，`set()` や `get()` の呼び出しとは独立に，バックグラウンドで動作するものがあります．例えば：

- PID ループやランピングなど，`set()`/`get()` の問い合わせとは独立にタスクを実行するノード
- データ取得に時間がかかる場合に，定期的にデータを先読みしてキャッシュに保存しておくノード

このようなノードは，`ControlThreadMixin` または `ControlAsyncTaskMixin` を継承して実装されます．

- `ControlThreadMixin`: ノードに `run()` メソッドがあれば，`start()` を呼ぶと専用のスレッドが作成され，その中で `run()` が実行されます．
- `ControlAsyncTaskMixin`: ノードに `async def aio_run()` メソッドがあれば，`start()` を呼ぶと asyncio のタスクが作成され，`aio_run()` が実行されます．

スレッドやタスクは，ノードの `stop()` メソッドを呼ぶか，全体の停止要求（`ControlSystem.stop()` やシグナルなど）により停止されます．
`run()` 関数は停止要求を（`is_stop_requested()` により）監視し，停止要求があったら自分で終了しなければなりません．
`aio_run()` の場合は，`stop()` によりタスクがキャンセルされ，次の `await` の時点で停止します．

例えば，ダミーデバイスの `first_order_plant` はスレッドでシミュレーションを走らせるノードで，以下のように使います．
```python
plant = ctrl.import_control_module('DummyDevice').first_order_plant(gain=0.1, noise=0.1)
plant.start()

while True:
    state = plant.get()   # 時間発展した内部状態
    ...
```

### よく使われるノード
命名規則：`set()`，`get()`，および `do_XXX()` は動作を行う通常のメソッドです．名詞の名前を持つメソッドは子ノードを返します．

#### Ethernet，SCPI，Telnet
##### ロード（組み込み済）
`ctrl.import_control_module('Ethernet')`

##### ノード
- **ethernet(host, port)**: TCP ソケット接続によりテキストメッセージを送受信する
  - set(value): 値をエンコードしたテキストとして送信する
  - get(): テキストのチャンクを受信する
  - do_get_chunk(timeout=None): テキストのチャンクを受信する
  - do_get_line(timeout=None): チャンクを受信し，（必要なら再構成して）一行を返す
  - do_flush_input(): 受信バッファを空にする
  - **scpi(timeout=10, line_terminator='\x0d', append_opc=False)**: 親のイーサネット接続を SCPI に橋渡しし，SCPI の設定を保持する
    - **command(cmd, set_format=None)**: 親のイーサネット接続を介して SCPI コマンドを発行する
      - set(value=None): `cmd value` を送信して応答を待つ
      - get(): `cmd?` を送信して応答を待ち，その応答を返す
  - **telnet(prompt, line_terminator)**: 親のイーサネット接続を Telnet に橋渡しし，Telnet の設定を保持する
    - **command(cmd)**: 親のイーサネット接続を介して Telnet コマンドを発行する
      - set(value=None): `cmd value 改行` を送信し，エコーを読み捨てる
      - get(): `cmd 改行` を送信し，エコーを読み捨て，次のプロンプトまでの応答を返す

#### シリアルポート
##### ロード
`ctrl.import_control_module('Serial')` （`pyserial` パッケージが必要）

##### ノード
- **serial(port='/dev/ttyUSB0', baudrate=115200)**: シリアルポート経由でテキストメッセージを送受信する
  - set(value): 値をエンコードしたテキストとして送信する
  - get(): テキストのチャンクを受信する
  - do_get_chunk(timeout=None): テキストのチャンクを受信する
  - do_get_line(timeout=None): チャンクを受信し，（必要なら再構成して）一行を返す
  - do_flush_input(): 受信バッファを空にする
  - **scpi()**: イーサネットノードの `scpi()` と同じもの

#### VISA
USB 接続や GPIB 接続，HiSLIP などを使用するデバイスは，VISA 経由で使用できます．
##### ロード
`ctrl.import_control_module('VISA')` （`pyvisa` パッケージが必要）

##### ノード
- **visa(resource_name)**: VISA リソース名（例：`USB0::0x2A8D::0x0201::MY54700218::0::INSTR`）で指定されるデバイス
  - **scpi()**: イーサネットノードの `scpi()` と同じもの

#### HTTP (Web API)
##### ロード（組み込み済）
`ctrl.import_control_module('HTTP')`

##### ノード
- **http(base_url)**:
  - **path(path)**: `base_url` に付加されるパス文字列
    - set(value): `base_url` + `path` に，`value` を内容とする POST リクエストを送る
    - get(): `base_url` + `path` に GET リクエストを送り，応答の内容を返す
    - **json()**: 
      - set(value): `value` は JSON に変換される Python オブジェクト
      - get(): JSON ドキュメントを受信し，Python オブジェクトとして返す
    - **value()**: ramping() などで使用するための ControlVariableNode を返す

async 版の `async_http(base_url)` も組み込まれています．

#### シェルコマンド
##### ロード（組み込み済）
`ctrl.import_control_module('Shell')`

##### ノード
- **shell(cmd)**: シェルコマンドを実行する
  - set(value): `cmd value` を起動する
  - get(): `cmd` を起動し，その出力を返す
  - **value()**: ramping() などで使用するための ControlVariableNode を返す
  - **arg(\*args)**: 親の "shell" ノードにプログラム引数を追加する <br>
    例：`adc0 = ctrl.shell('read_adc').arg('--ch=0')`
    - **value()**: ramping() などで使用するための ControlVariableNode を返す
    
#### SlowDash サーバーへのアクセス
##### ロード
HTTP ノードにロードします：`ctrl.http(url).import_control_module('Slowdash')`

##### ノード
- **http(url).slowdash()**
  - **ping()**: `pong` を返す
  - **channels()**: チャンネルリストの JSON オブジェクトを取得する
  - **data(channels, length=3600)**: 指定したチャンネルのデータの JSON オブジェクトを取得する
  - **config()**: プロジェクト設定の JSON オブジェクトを取得する
  - **config_file(name)**: 設定ファイルを取得または送信する

async 版として，`async_http(url)` にロードする `AsyncSlowdash` プラグイン (`async_slowdash()`) もあります．
  
#### その他のノード（抜粋）
- Redis（`redis` パッケージを使用）
- RabbitMQ（`pika` および `aio-pika` を使用）
- MQTT（`paho-mqtt` および `aio-mqtt` を使用）
- NATS（`nats-py` を使用）
- Modbus（`pymodbus` を使用）
- LabJack（`LabJackPython` を使用，現時点では U3/U6/U12 のみサポート）
- UDP
- DataStore（`data_store(url).tag(name)` に `set()` するとデータベースに記録される）
- DummyDevice（ランダムウォークやイベントジェネレータ，一次・二次遅れ系のプラントなど，テスト用のダミーデバイス）

SlowPy のコントロールプラグインは `slowdash/lib/slowpy/slowpy/control` 以下に `control_XXX.py` という名前で置かれています．
使い方の例は `slowdash/lib/slowpy/test` 以下のテストスクリプトを参照してください．

### ノードの共通関数
全てのコントロールノード（`slowpy.control.ControlNode` の派生クラス）は以下のメソッドを持ちます．

- [ControlNode]
  - **has_data()**: `get()` で取得できる値があれば True を返す
  - **wait(condition_lambda=None, poll_interval=0.1, timeout=0)**: `condition_lambda` が None でない場合は，`condition_lambda` が `True` を返すまでブロックする．`condition_lambda` が None の場合は，`has_data()` が True を返すまで待つ．タイムアウトの場合は `None` を返し，停止要求があった場合は `False` を返す．それ以外の場合は `True` を返す．
  - **sleep(duration_sec)**: 指定時間ブロックする．停止要求を受け取らなければ True を返す．
  - **is_stop_requested()**: 停止要求を受け取っていれば True を返す
  - **snapshot()**: `get()` で得た値を保持し，子ノードの `get()` に同じ値を返すノードを返す（一回の読み出しで得たデータの各フィールドを，子ノードを通して取り出す場合などに使用）

`wait()` と `sleep()` には，async 版の `aio_wait()` と `aio_sleep()` もあります．

`ControlVariableNode` から派生したノードは，以下のメソッドを持ちます．

- [ControlVariableNode] -> [ControlNode]
  - **setpoint(limits=(None,None))**: セットポイントを保持する
    - set(value): 値をセットポイントとして保持し，親ノードの `set(value)` を呼ぶ．値が limits の範囲外の場合は例外を発生する．
    - get(): 保持しているセットポイントの値を返す
  - **ramping(change_per_sec)** / **async_ramping(change_per_sec)**: 値をランプさせながら設定する（スレッド版 / async タスク版）
    - set(value): 親ノードの値を目標値に向けてランピングを開始する．値が数値でない場合は例外を発生する．
    - get(): 親ノードの `get()` を返す
    - **status()**
      - set(value): `set(0)` で実行中のランピングを停止する
      - get(): ランピング中であれば `True` を，そうでなければ `False` を返す
  - **pid(sensing_node, Kp, Ki, Kd, \*, interval=1.0, output_limits=(None,None))**: `sensing_node` から読んだ値を使って，このノードを PID 制御する
    - set(value): センサーノードの値が目標値となるように PID ループを開始する．`set(None)` で制御を停止する．
    - get(): 目標値を返す
    - **status()**
      - set(value): `set(0)` で PID ループを停止する
      - get(): 各種の制御パラメータ（`running`, `setpoint`, `measurement`, `output`, `Kp`, `Ki`, `Kd` など）を含んだ dict を返す
  - **oneshot(duration=None, normal=None)**: `set()` した値を指定時間だけ保持し，その後 `normal` の値に戻す
  - **readonly()**: ノードを読み出し専用にする．親ノードの `get()` を呼ぶ `get()` だけを持つノードを返す．（ノードを外部に公開する場合に便利）
  - **writeonly()**: ノードを書き込み専用にする．親ノードの `set()` を呼ぶ `set()` だけを持つノードを返す．

`ControlThreadMixin` または `ControlAsyncTaskMixin` を継承したノードは，以下のメソッドを持ちます．

- [ControlThreadMixin / ControlAsyncTaskMixin]
  - **start()**: `run()`（スレッド）または `aio_run()`（async タスク）を作成して開始する
  - **stop()**: スレッドまたはタスクを停止する


## データベースインターフェース
SlowPy の DataStore を使うと，SlowDash で読める形式でデータベースにデータを記録できます．
以下は，ロングフォーマットのテーブルに単一の値を書き込む簡単な例です．
```python
from slowpy.control import control_system as ctrl
from slowpy.store import DataStore_PostgreSQL

device = ctrl.import_control_module('DummyDevice').randomwalk_device()
datastore = DataStore_PostgreSQL('postgresql://postgres:postgres@localhost:5432/SlowTestData', table="Test")

while True:
    for ch in range(4):
        value = device.ch(ch).get()
        datastore.append(value, tag='%02d'%ch)

    ctrl.sleep(1)
```

以下の DataStore クラスがあります．

| クラス | URL 形式 | 備考 |
|---|---|---|
| `DataStore_SQLite` | `sqlite:///FILE_NAME` | 第２引数はテーブル名 |
| `DataStore_PostgreSQL` | `postgresql://USER:PASS@HOST:PORT/DB` | 第２引数はテーブル名 |
| `DataStore_MySQL` | `mysql://USER:PASS@HOST:PORT/DB` | 第２引数はテーブル名 |
| `DataStore_InfluxDB2` | `influxdb2://ORGANIZATION:TOKEN@HOST:PORT/BUCKET` | 第２引数は measurement 名 |
| `DataStore_Redis` | `redis://HOST:PORT/DB` | |
| `DataStore_HDF5` | （ファイル名） | 第２引数はデータセット名．ランごとのファイル記録など |
| `DataStore_CSV` | `csv:///FILE_NAME` | |

URL から適切な DataStore を作成する `create_datastore_from_url(url, table)` 関数もあります．設定ファイルなどからデータベースの URL を受け取る場合に便利です．
```python
from slowpy.store import create_datastore_from_url
datastore = create_datastore_from_url('sqlite:///SlowStore.db', 'slowdata')
```

DataStore の主なメソッドは以下のとおりです．

- **append(values, tag=None, timestamp=None)**: 値を時系列データとして追加する
- **update(values, tag=None, timestamp=None)**: 値を更新する（最新値のみを保持する）
- **another(table)**: 同じデータベースの別のテーブルに書き込む DataStore を返す（SQL 系のみ）
- **close()**: データベースとの接続を閉じる

`values` には，数値や文字列の他，ヒストグラムなどの解析オブジェクト（後述）を渡すことができます．
`timestamp` は UNIX 時刻で，省略した場合は現在時刻が使われます．

SQL データベースでは，デフォルトで UNIX タイムスタンプを使用した「ロングフォーマット」(`(timestamp REAL, channel VARCHAR(100), value REAL)`) が使われます．
他のテーブルスキーマを使用するには，ユーザー定義の `TableFormat` を指定します．
```python
from slowpy.store import DataStore_SQLite, LongTableFormat

class MyDataFormat(LongTableFormat):
    schema_numeric = '(datetime DATETIME, timestamp INTEGER, channel VARCHAR(100), value REAL, PRIMARY KEY(timestamp, channel))'
    schema_text = '(datetime DATETIME, timestamp INTEGER, channel VARCHAR(100), value TEXT, PRIMARY KEY(timestamp, channel))'

    def insert_numeric_data(self, cur, timestamp, channel, value):
        ph = self.db.placeholder
        cur.execute(f'INSERT INTO {self.table} VALUES(CURRENT_TIMESTAMP,{ph},{ph},{ph})', (int(timestamp), channel, value))

    def insert_text_data(self, cur, timestamp, channel, value):
        ph = self.db.placeholder
        cur.execute(f'INSERT INTO {self.table} VALUES(CURRENT_TIMESTAMP,{ph},{ph},{ph})', (int(timestamp), channel, str(value)))

datastore = DataStore_SQLite('sqlite:///MySlowStore.db', table="slowdata", table_format=MyDataFormat())
```

複数の SlowTask からデータを記録する場合は，各タスクが直接データベースに書き込む代わりに，データを SlowMesh に publish し，記録専用の一つの SlowTask でまとめてデータベースに書き込むようにするのが便利です（後述の SlowMesh の節を参照）．
これにより，SQLite のような同時書き込みに制限があるデータベースでも競合を避けることができ，また，テーブルスキーマの記述も一箇所にまとめられます．

## 解析部品
SlowPy は，ヒストグラムやグラフなどのよく使われるデータオブジェクトを提供しています．
これらのオブジェクトは，上記の SlowPy データベースインターフェースを使って，そのままデータベースに書き込むことができます．
また，後述のストリーミング機能を使って，データベースを経由せずにブラウザに直接送ることもできます．

### ヒストグラム
```python
import slowpy
hist = slowpy.Histogram(nbins=100, range_min=0, range_max=10)

device = ...
datastore = ...

while True:
  value = device.read(...
  hist.fill(value)

  if time_to_store:
    datastore.append(hist, tag="test_hist")
  ...
```

`datastore.append(hist, tag=name)` は，ヒストグラムの時系列（時刻ごとに一つのヒストグラム）を作成します．
最新のヒストグラムだけを保持するには，代わりに `datastore.update(hist, tag=name)` を使ってください．

`clear()` でヒストグラムの内容をクリアできます．
また，`add_stat()` により，エントリ数や平均値などの統計量をヒストグラムに付加して表示させることができます．
```python
hist.add_stat(slowpy.HistogramBasicStat(['Entries', 'Underflow', 'Overflow', 'Mean', 'RMS'], ndigits=3))
```
２次元ヒストグラム `Histogram2d(xnbins, xrange_min, xrange_max, ynbins, yrange_min, yrange_max)` もあります．

### グラフ
```python
import slowpy
graph = slowpy.Graph(['channel', 'value'])

while True:
  for ch in range(n_ch):
    value = device.read(ch, ...
    graph.fill(ch, value)
  if time_to_store:
    datastore.append(graph, tag="test_graph")
  ...
```

`datastore.append(graph, tag=name)` は，グラフの時系列（時刻ごとに一つのグラフ）を作成します．
最新のグラフだけを保持するには，代わりに `datastore.update(graph, tag=name)` を使ってください．
ヒストグラム同様，グラフにも `add_stat()` があります．

### トレンド
Trend とは，データを時間ビンごとに区切り，それぞれのビンについて平均などを計算する特殊なグラフです．
データ値の平均値などを保持する通常の Trend と，データの数（レート）を保持することに特化した RateTrend があります．

```python
import slowpy
rate_trend = slowpy.RateTrend(length=300, tick=10)

while True:
  value = device.read(...
  rate_trend.fill(time.time())

  if time_to_store:
    datastore.append(rate_trend.timeseries())
    rate_trend.flush()
```

Histogram や Graph とは異なり，Trend はデータベースに記録する際，一つのオブジェクトとして記録するのではなく，時系列データに展開して記録します．
このために，`timeseries()` メソッドが使われています．
（トレンドオブジェクト自体を保存することもできますが，通常は行いません．）
また，データベースに記録した部分のデータを削除するため，記録後に `flush()` を呼んでいます．（`timeseries(flush=True)` としても同じです．）

ブラウザにストリーミングする場合は，保持している過去のデータはすべて表示したいので，`flush()` をせずに，`timeseries()` の結果を毎回全て送ります．
```python
await ctrl.aio_stream('rate_trend', rate_trend.timeseries())
```

## デバイスの SCPI 化
Raspberry Pi の GPIO のように，デバイスに何らかのプログラミング機能がある場合，それを SlowDash システムに統合する簡単な方法は，そのデバイス上に SCPI インターフェースを実装することです．
この方法は，リモートコンピュータに接続された（USB などの）イーサネット以外のデバイスを Raspberry-Pi などを介して統合する場合にも便利です．

以下は，デバイスをイーサネット SCPI でラップする例です．

```python
from slowpy.control import ScpiServer
scpi = ScpiServer()

class MyMemoryDevice:
    def __init__(self):
        self.value = 0
device = MyMemoryDevice()

@scpi.on('*IDN?')
def get_idn():
    return 'MyMemoryDevice'

@scpi.on('Volt')
def set_V(value:float):
    device.value = value
    
@scpi.on('MEASure:Volt?')
def get_V():
    return device.value

scpi.start(port=5025)
```

これにより以下の SCPI コマンドが実装されます（コマンドは大文字小文字を区別しません）：

| コマンド | 動作 | コマンド例 | 戻り値例 |
|---|---|---|---|
| `*IDN?` | デバイスIDを返す | `*IDN?` | `MyMemoryDevice` |
| `Volt <Value>` | 値を設定する | `V 10` | (なし) |
| `MEASure:Volt?` | 値を取得する | `MEAS:V?` | `10` |
| `*OPC?` | コマンドの完了を待ち，ステータスを返す | `*OPC?` | `1` |
| `SYSTem:ERRor?` | エラーメッセージを返す | `SYST:ERR?` | `invalid command: IDN?` <br>(前に `*IDN?` を `IDN?` とした) |

SlowPy の SCPI サーバーでは，デコレーターを使って SCPI コマンドとハンドラを結びつけています．
この例の `set_V(value:float)` のように，ハンドラ関数の引数に型アノテーションをつけると，呼び出し時に型チェックと型変換を行います．
SCPI のコマンド連結などはハンドラが呼び出される前に処理されます．
`*OPC?` や `SYSTem:ERRor?` などの一部の標準コマンドに対してはデフォルトのハンドラ実装があります．

コードのテストができたら，好みの方法（systemd，`/etc/rc.local`，Docker など）で，PC 起動時に自動で開始するようにしてください．
[関連ツール](RelatedTools_JP.html)に，いくつかの方法が説明してあります．

そのデバイスに対する SlowPy のコントロールノードがすでにある場合は，ノードを直接 SCPI インターフェースにマップできます．
```python
from slowpy.control import ControlSystem, ScpiServer, ScpiAdapter

ControlSystem.import_control_module('DummyDevice')
device = ControlSystem().randomwalk_device()

adapter = ScpiAdapter(idn='RandomWalk')
adapter.bind_nodes([
    # Randomwalk Configuration
    ('CONFIGure:WALK', device.walk().setpoint(limits=(0,None))),
    ('CONFIGure:DECAY', device.decay().setpoint(limits=(0,1))),

    # Common SCPI commands for power supplies and voltmeters
    ('VOLTage', device.ch(0).setpoint()),
    ('MEASure:VOLTage:DC', device.ch(0).readonly()),
])

server = ScpiServer(adapter, port=5025)
server.start()
```

# SlowTask: GUI とスクリプトの結合
SlowTask は，SlowDash プロジェクトの `config` ディレクトリの下に `slowtask-XXX.py` のような名前で置かれたユーザーの Python スクリプトです．
SlowDash の GUI から，スクリプトの開始・停止，スクリプト中で定義された関数の呼び出し，スクリプト中の変数の表示などを行えます．
SlowPy ライブラリは SlowTask スクリプトで使用することを想定して設計されていますが，使用は必須ではありません．

SlowTask スクリプトには，以下の２つの書き方があります．

- **Tasklet を使用する**：スクリプト中で `slowpy.mesh.Tasklet` のインスタンスを作成し，デコレーターを使って，外部に公開する関数や，開始時・一定時間間隔などで呼び出される関数を明示的に指定する．SlowMesh の全ての機能を使用できる．
- **Tasklet を使用しない**：普通の Python スクリプトをそのまま使う．アンダースコアで始まらない全ての関数が外部から呼べるようになり，`_initialize()` や `_loop()` などの決められた名前の関数が，特定のタイミングで呼ばれる．使える機能は限られる．

Tasklet を使用しない方法は，既存のスクリプトをそのまま SlowDash Web GUI で使いたい場合や，スクリプトの中に SlowPy コードを書きたくない場合のためのものです．
新しくスクリプトを作成する場合は，Tasklet を使用した方が管理しやすく高機能です．

```python
from slowpy.mesh import Tasklet
tasklet = Tasklet()

... (本文) ...

# スクリプトを単体で実行するためのブロック（オプション）
if __name__ == '__main__':
    tasklet.run(mesh_url='slowmq://localhost:18881')
```

## SlowTask の開始と停止
### SlowDash サーバーからの開始
SlowTask のスクリプトファイル（例えば `slowtask-test.py`）をプロジェクトの `config` ディレクトリの下に置くと，SlowDash サーバーに認識され，SlowDash のホーム画面のタスク管理パネル（"SlowTask" セクション）に表示されます．
デフォルトでは，タスクは「リスト」されるだけで，`start` ボタンがクリックされるまで実行されません．

SlowDash の設定ファイル (`SlowdashProject.yaml`) にエントリを作ると，サーバーの開始時に自動でタスクを開始するように設定できます．
```yaml
slowdash_project:
  ...

  task:
    name: test
    auto_start: true
    parameters:
      default_ramping_speed: 0.1

  system:
    our_security_is_perfect: false
```

`task` エントリには一つのタスクの dict か，複数のタスクのリストを指定できます（`task` の代わりに `tasks` と書いても構いません）．
```yaml
  tasks:
    - name: read
      auto_start: true
    - name: store
      auto_start: true
      parameters:
        db_url: sqlite:///SlowStore.db
        table: slowdata
```

| パラメータ | 内容 | デフォルト |
|---|---|---|
| `name` | タスク名 | （必須） |
| `auto_start` | サーバー開始時にタスクを自動で開始するか（旧名 `auto_load` も使用可） | `false` |
| `parameters` | スクリプトに渡すパラメータ | なし |
| `file_path` | スクリプトファイルのパス | `config/slowtask-{name}.py` |
| `command` | タスクの開始コマンド | `slowdash-task {file_path} --name={name}` |

`parameters` は省略可能で，指定した場合は SlowTask スクリプトの initialize コールバック（後述）に渡されます．また，Tasklet の `parameters` プロパティにも保持され，デコレーターなど `initialize` 前でも使用できます．

`command` を変更すると，例えば `ssh` を使って別の PC 上でタスクを実行することもできます．
同じスクリプトを異なる名前で複数のエントリに書けば，同じスクリプトを複数同時に走らせることもできます．

SlowDash の配布パッケージに含まれている汎用 SlowTask を使用する場合は，`name` に `@toolbox/` を付加します．
詳しくは [Toolbox の章](Toolbox_JP.html) を参照してください．

`system` の `our_security_is_perfect` を `true` にすると，SlowDash のウェブページ上で Python スクリプトを編集できるようになります．
これは便利ですが，その意味をよく考えてください．
Python スクリプトは `system("rm -rf *")` など何でもできます．
アクセスが厳格に管理されている場合にのみ，この機能を使用してください．

### SlowDash サーバーからのタスク操作
SlowDash のタスク管理パネルからは，以下のような SlowTask の操作を行えます：

- **Start**: SlowTask を子プロセスとして開始する．開始コマンドは `SlowdashProject.yaml` ファイルの `command` で指定でき，デフォルトは `slowdash-task` コマンドによるローカル実行．
- **Stop**: SlowMesh 経由でタスクに停止を要求する．Tasklet の停止処理が行われ，finalize コールバックが呼ばれる．
- **Kill**: タスクをサーバーから子プロセスとして実行した場合，子プロセスに KILL シグナルを送る．
- **Purge**: 応答がなくなったタスクを SlowMesh から抹消する．

SlowDash サーバーから起動された SlowTask プロセスは，SlowDash サーバーが終了したときに自動で終了します．
（サーバーのクラッシュや強制終了の場合でも，SlowTask プロセスは自動で終了します．）

スクリプトを書き換えた場合は，タスクを Stop してから Start し直すと，新しいスクリプトが読み込まれます．

### サーバーとは独立に実行
SlowTask を SlowDash サーバーから独立したプロセスとして実行するには，通常は `slowdash-task` コマンドを使います．
`--mesh` オプションで SlowMesh の接続先（通常は SlowDash サーバーのアドレス）を指定します．
`--parameters` オプションに JSON 文字列を渡すことにより，タスクパラメータも渡すことができます．
この場合は，JSON 文字列がシェルによって誤って処理されないようにするために，全体をシングルクオートで囲ってください．
```console
$ cd PATH/TO/PROJECT
$ slowdash-task config/slowtask-mytask.py --mesh=slowmq://localhost:18881 --parameters='{"p1":10,"p2":20}'
```

もしスクリプト中で `if __name__ == '__main__': tasklet.run(...)` をしているなら，通常の Python スクリプトとしての実行もできます．
ただし，この場合は，タスクパラメータを渡すことはできません．
```console
$ slowdash-activate-venv
$ python config/slowtask-mytask.py
```

独立に開始した SlowTask プロセスでも，SlowDash サーバーから停止操作 (Stop) を行えます．
ただし，サーバーからの強制終了 (Kill) はできません．
独立に開始した SlowTask プロセスは，SlowDash サーバーが止まっても走り続け，次に SlowDash サーバーが開始したときに，自動的に再接続されます．
タスクが SlowMesh にアクセスできる限り，タスクプロセスを別の PC や別のコンテナ上で実行しても構いません．

### タスク名
各 SlowTask には名前（タスク名）がつけられ，ブラウザなどからの関数呼び出しや，データチャンネル名などに使われます．
タスク名は，以下のいずれかで指定されます．

- タスクスクリプトのファイル名から，先頭の `slowtask-` を除いたもの（デフォルト）
- `SlowdashProject.yaml` の `task` エントリの `name` パラメータ
- `slowdash-task` コマンドの `--name` パラメータ
- `Tasklet.run()` の `name` 引数

タスク名には，英数字および `_` 以外の文字は使用できません．
これらの文字が含まれる場合は，`_` に置き換えられます．
例えば，`slowtask-my-device.py` のタスク名は `my_device` になります．

## 関数のエクスポート
SlowTask スクリプト中のユーザー関数は，Web GUI をはじめとする外部から呼び出すことができます．

### Tasklet を使用する場合
SlowTask スクリプトの中で Tasklet を使用している場合，Web GUI などから呼び出される関数は `@tasklet.mesh.export()` デコレーターを使って明示的に指定しなければなりません．
これにより，スクリプトが長くなったときでも，どの関数が外部から呼ばれるのかが明確になります．

```python
from slowpy.mesh import Tasklet
tasklet = Tasklet()

@tasklet.mesh.export()
async def set_V(ch:int, V0:float, ramping:float):
    ...
```
関数は通常の関数と async 関数のどちらでも構いません．
関数を別の名前でエクスポートする場合は，`@tasklet.mesh.export(name='set_voltage')` のように，`name` をキーワード引数で指定します．

### Tasklet を使用しない場合
スクリプトの中で Tasklet を使用していない場合，名前がアンダースコア (`_`) で始まらない全ての関数が暗黙にエクスポートされます．
（そのスクリプトで定義された関数のみが対象で，import した関数はエクスポートされません．）

```python
def set_V(ch:int, V0:float, ramping:float):
    ...
```

### エクスポートした関数の実行時間について
SlowTask は全体がシングルスレッドの非同期処理で並行に動いているので，スクリプトの中で `time.sleep()` を使うと全体が固まってしまいます．
後述の `@tasklet.loop(interval)` などを使ってループを書くことにより，スクリプトの中で明示的な sleep をしないのが想定です．
どうしても sleep をする場合は，`await asyncio.sleep()` または `await ctrl.aio_sleep()` を使ってください．

また，**エクスポートした関数の実行は即座に終了するようにして，最大 1 秒を目安に return するようにしてください**．
呼び出し側はデフォルトで 5 秒でタイムアウトします．
時間がかかる処理は，以下の方法を検討してください：

- 処理要求を変数にセットするか `asyncio.Queue` に入れて，`@tasklet.loop()` のコールバックでそれを見て処理を開始する
- `asyncio.create_task()` で別のタスクとして実行する
- ランピングや PID などのように，スレッドや async タスクを持つ SlowPy のノードを使う

処理の状況や結果は，ストリーミングなどでブラウザに送ったり，ログに書いたりするのが想定です．

## Web GUI からの関数呼び出し
エクスポートした関数は，SlowDash の GUI からいくつかの方法で呼び出すことができます．
以下では，スクリプトファイル名が `slowtask-test.py`（タスク名 `test`）であるとします．

### HTML フォームパネル
SlowPlot の HTML フォームパネルで，タスク名と関数名を `name` 属性に持つ `<button>`（または `<input type="submit">`）をクリックすると，その関数が呼ばれます：
```html
<form>
  <button name="test.destroy_apparatus()">Finish</button>
</form>
```
ここで，ボタン名の最後の括弧は，このボタンが SlowTask の関数に結び付けられていることを示しています．

先頭の部分（この例では `test.`）はタスク名で，デフォルトでは，スクリプトのファイル名から先頭の `slowtask-` を除いたものになります．
（タスク名に `-` が含まれる場合は `_` に置き換えられます．）

HTML ファイルは，プロジェクトの `config` ディレクトリに `html-XXX.html` という名前で置きます．
後述のように，SlowTask スクリプトの中で HTML の内容を生成することもできます．

#### パラメータの受け渡し
SlowTask の関数は引数を取ることができます：
```python
def set_V0(voltage:float, ramping:float):
    #... do your work here
```
引数の値は，フォームの `<input>` の値から取られます：
```html
<form>
  Voltage: <input type="number" name="voltage" value="0"><br>
  Ramping: <input type="number" name="ramping" value="1"><br>
  <button name="test.set_V0()">Set</button>
</form>
```
`<input>` の `name` 属性が，関数の引数名に対応します．
フォーム中の `<input>` のうち，関数が受け取る引数のものだけが渡されます．

上の例のように SlowTask 関数に型アノテーションをつけると，引数の値は指定された型に変換されます．
値が指定された型に変換できない場合は，ブラウザにエラーが返され，SlowTask 関数は呼ばれません．
チェックボックス (`<input type="checkbox">`) の値は，`bool` 型の引数に渡すことができます．

一つのフォームに複数のボタンを配置することもできます：
```html
<form>
  Ramping: <input type="number" name="ramping" value="1" style="width:5em">/sec
  <p>
  V0: <input type="number" name="V0" value="0"><button name="test.set_V0()">Set</button><br>
  V1: <input type="number" name="V1" value="0"><button name="test.set_V1()">Set</button><br>
  V2: <input type="number" name="V2" value="0"><button name="test.set_V2()">Set</button><br>
  V3: <input type="number" name="V3" value="0"><button name="test.set_V3()">Set</button><br>
  <p>
  <button name="test.set_all()">Set All</button>
  <button name="test.stop()">Stop Ramping</button><br>
</form>
```
```python
def set_V0(V0:float, ramping:float):
    ...

def set_V1(V1:float, ramping:float):
    ...
```
Web フォームの入力値は，名前に基づいて関数の引数に結び付けられます（`<input name="V0">` は引数 `V0` に結び付けられます）．

関数の引数を `<input>` から渡す代わりに，`<button>` の名前の中に直接書くこともできます．

```html
<form>
  Ramping: <input type="number" name="ramping" value="1" style="width:5em">/sec
  <p>
  V0: <input type="number" name="V0" value="0"><button name="test.set_V(ch=0)">Set</button><br>
  V1: <input type="number" name="V1" value="0"><button name="test.set_V(ch=1)">Set</button><br>
  V2: <input type="number" name="V2" value="0"><button name="test.set_V(ch=2)">Set</button><br>
  V3: <input type="number" name="V3" value="0"><button name="test.set_V(ch=3)">Set</button><br>
  <p>
  <button name="test.set_all()">Set All</button>
  <button name="test.stop()">Stop Ramping</button><br>
</form>
```
```python
def set_V(ch:int, V0:float, ramping:float):
    ...
```

（以前のバージョンで使われていた `reentrant` や `async` などの実行コントロールは，Python スクリプト側に移されました(TODO)．ボタン名の修飾子は，現在は不要で，指定しても警告が出て無視されます．）

#### PubSub への Publish
ボタン名を `publish トピック名()` とすると，関数を呼ぶ代わりに，フォームの入力値を SlowMesh の指定トピックに publish します．
特定のタスクの関数を呼ぶのではなく，「スタート」などのイベントを，それを必要とする全てのタスクに知らせる場合に使います（SlowMesh の節を参照）．
```html
<form>
  <button name="publish mydaq.control.start()">Start</button>
  <button name="publish mydaq.control.stop()">Stop</button>
</form>
```
publish されるデータは，括弧内の引数とフォームの `<input>` の name-value 対を合わせた dict です．

#### フォームの同期
`<form>` に名前を付けると，`<input>` の change のたびに値がサーバーへ送られ，複数ブラウザ上でフォームの入力値が（ボタンを押す前でも）同期されます．
また，フォームの値はプロジェクトディレクトリのファイル (`registry-pubsub-form.json`) に保存され，サーバーの終了・再スタート時に，以前のフォームの値が自動で設定されるようになります．
```html
<form name="voltage_control">
  Ramping: <input type="number" name="ramping" value="1" style="width:5em">/sec
...
</form>
```

名前を付けたフォームの値は，SlowTask スクリプトから読み書きすることもできます（後述の「フォーム値の読み書き」を参照）．

#### データによるボタンの有効・無効の切り替え
`<input>` に `sd-enabled` 属性を指定すると，データの値に応じてボタンなどの有効・無効を切り替えられます．
SlowTask からストリーミングまたはエクスポートした値（後述）を使えば，タスクの状態に応じて，例えば実行中は Start ボタンを無効にする，といったことができます．
```html
<form name="run_control">
  <input type="submit" name="test.start()" value="Start" sd-enabled="run_status['running']->invert()">
  <input type="submit" name="test.stop()" value="Stop" sd-enabled="run_status['running']">
</form>
```
`sd-enabled` に指定する値は真偽値である必要があります．値の変換については [Data Transform の章](DataTransform.html) を参照してください．

### キャンバスパネル
キャンバスパネルでは，タスクを呼び出すボタンは以下のように配置できます：
```json
{
    ...
    "items": [
        {
            "type": "button",
            "attr": { "x":400, "y": 630, "width": 130, "label": "Finish Experiment" },
            "action": { "submit": { "name": "test.destroy_apparatus()" } }
        },
        ...
```

引数を取る関数に対しては，フォームを使用できます：
```json
{
    ...
    "items": [
        {
            "type": "valve", 
            "attr": { ... },
            "metric": { "channel": "sccm.GasInlet", ... },
            "action": { "form": "FlowControl" }
        },
        ...
    ],
    "forms": {
        "FlowControl": {
            "title": "Injection Flow",
            "inputs": [
                { "name": "flow", "label": "Set-point (sccm)", "type": "number", "initial": 15, "step": 0.1 }
            ],
            "buttons": [
                { "name": "ATDS.set_flow()", "label": "Apply Set-point" },
                { "name": "ATDS.stop_flow()", "label": "Close Valve" }
            ]
        }
    }
    ...
```

詳しくは，[UI パネルの章](Panels.html) を参照してください．

### 他の SlowTask やプログラムからの呼び出し
エクスポートした関数は，SlowMesh の遠隔関数呼び出し (RPC) により，他の SlowTask から呼び出すこともできます．
```python
return_value = await tasklet.mesh.aio_call('test.set_V', ch=0, V0=10, ramping=1)
```
また，HTTP API（`api/control` への POST）を使えば，ブラウザ以外のプログラムから呼び出すこともできます．

## ライフスパンコールバック
### Tasklet を使用する場合
tasklet が提供するデコレーターにより，特定のタイミングや一定時間間隔に SlowTask 中の関数を呼び出すことができます．
呼び出される関数は通常の関数と async 関数のどちらでも構いません．（ただし，関数の中で `time.sleep()` は使用しないでください．）

同じデコレーターを複数回使用することもできます．
特に，処理ごとに小さな `@tasklet.loop(interval)` 関数を複数作れば，スクリプト中に自分でループを書く必要がなくなり，スリープや終了処理などの煩雑さを避けられます．

- `@tasklet.initialize()`: スクリプト開始時に呼ばれる
- `@tasklet.finalize()`: スクリプト終了時に呼ばれる
- `@tasklet.once(delay:float=0)`: initialize から指定秒数後に一度だけ呼ばれる
- `@tasklet.schedule(time:str, use_utc:bool=False)`: 指定時刻に繰り返し呼ばれる
- `@tasklet.loop(interval:float, ticks=None)`: 指定秒数間隔で繰り返し呼ばれる

#### 初期化と終了処理
`@tasklet.initialize()` の関数が引数を一つ持つ場合，`SlowdashProject.yaml` の `parameters`（または `slowdash-task` コマンドの `--parameters`）で指定したタスクパラメータが dict として渡されます．
```python
@tasklet.initialize()
async def initialize(parameters:dict):
    db_url = parameters.get('db_url', 'sqlite:///SlowStore.db')
    ...

@tasklet.finalize()
async def finalize():
    datastore.close()
```
タスクパラメータは `tasklet.parameters` からも取得できます．

全ての initialize コールバックが終了してから，loop や once などの他のコールバックが開始されます．
finalize コールバックは，タスクの停止要求（ブラウザからの Stop や Ctrl-c など）の後，他のコールバックが停止してから呼ばれます．

#### 定時実行
`@tasklet.schedule(time)` デコレーターにより，ユーザー関数を指定時刻に繰り返し呼び出すようにできます．

```python
@tasklet.schedule("08:00")
def do_this_every_morning():
   # 毎朝８時に実行
   pass
```

引数の `time` は `HH:MM` 形式で指定します．`HH` および `MM` には，ワイルドカード `*` を指定でき，また，複数の時刻設定を `,` 区切りで並べることができます．夏時間への切替時に周期が変わらないようにするためには，`use_utc` を `True` にして，時刻を UTC で指定してください．

例）

- `@tasklet.schedule("08:00")`: 毎朝８時
- `@tasklet.schedule("00:00,08:00,16:00")`: 一日３回
- `@tasklet.schedule("*:00")`: 毎時０分
- `@tasklet.schedule("*:*")`: 毎分
- `@tasklet.schedule("*:00,*:20,*:40")`: 毎時３回
- `@tasklet.schedule("08:00", use_utc=True)`: 毎日 UTC ８時

`use_utc` が指定されない限り，時刻はローカル時刻ですが，Docker などのコンテナの中などで実行される場合は，ローカル時刻が UTC となっていることが多いことに注意してください．

#### ユーザーループ
`@tasklet.loop(interval)` デコレーターにより，ユーザー関数を指定周期で繰り返し呼び出すようにできます．

```python
@tasklet.loop(interval=1)
async def my_work():   # この関数は１秒（interval の値）ごとに呼ばれる
    #... do my work
    pass
```

さらに，`@tasklet.loop` に `ticks` を指定し，ユーザー関数に `tick` 引数を追加すると，`ticks` に指定した回数ごとに `tick` の値が True になります（ユーザー関数の引数名は任意です）．
```python
@tasklet.loop(interval=1, ticks=10)
async def my_work(tick):
    # １秒毎にデータを読み，全てのデータをストリームに流す
    data = await HV.ch(0).aio_get()
    packet = DataPacket(data, tag='HV.ch00')
    
    await tasklet.mesh.aio_publish(packet.to('data.stream'))
    
    # データベースへの記録は１０回に１回
    if tick:
        await tasklet.mesh.aio_publish(packet.to('data.store'))
```

複数の tick 周期を指定することもできます．
```python
@tasklet.loop(interval=1, ticks={"transient_store":10, "store":60})
async def my_work(tick):
    # １秒毎にデータを読み，全てのデータをストリームに流す
    data = await HV.ch(0).aio_get()
    packet = DataPacket(data, tag='HV.ch00')
    
    await tasklet.mesh.aio_publish(packet.to('data.stream'))
    
    # 一時データベース（短期間高密度）への記録は１０回に１回
    if tick.transient_store:
        await tasklet.mesh.aio_publish(packet.to('data.transient_store'))
        
    # 永続データベースへの記録は６０回に１回
    if tick.store:
        await tasklet.mesh.aio_publish(packet.to('data.store'))
```
（`DataPacket` と `aio_publish()` については，後述の SlowMesh の節を参照してください．）

繰り返しますが，ユーザー関数の中で `time.sleep()` は使わないでください．(`await ctrl.aio_sleep()` は可）．
`@tasklet.loop()` を使うことにより，ほとんどの sleep をなくすことができるはずです．

### Tasklet を使用しない場合
もしスクリプトの中で Tasklet を使用していない場合，以下の関数が定義されていれば，それぞれ特定のタイミングで呼び出されます．

| 関数 | 説明 | Tasklet での相当 |
|---|---|---|
| `_initialize(params)` | スクリプトのロード時に一度呼ばれる．`params` の値は SlowDash の設定で与えられる． | `@tasklet.initialize()` |
| `_run()` | `_initialize()` の後に一度呼ばれる． | `@tasklet.once()` |
| `_loop()` | `_initialize()` の後，ユーザーがシステムを停止するまで繰り返し呼ばれる． | `@tasklet.loop(interval=0)` |
| `_finalize()` | `_run()` または `_loop()` の後に一度呼ばれる． | `@tasklet.finalize()` |
| `_get_html()` | HTML コンテンツを返す（後述）． | `@tasklet.content('html-{タスク名}.html')` |
| `_get_layout()` | SlowPlot レイアウトを返す（後述）． | `@tasklet.content('slowplot-{タスク名}.json')` |

Tasklet を使用した場合と異なり，`_loop()` 関数はスリープせずに即座に繰り返し呼ばれることに注意してください．
このため，`_loop()` の中で，周期を調整するためのスリープを行う必要があります．
呼び出される関数は通常の関数と async 関数のどちらでも構いませんが，`_loop()` に関しては，`time.sleep()` の使用を避けて代わりに `await ctrl.aio_sleep()` などを使用するために，async である必要があります．
```python
from slowpy.control import control_system as ctrl

async def _loop():
    ...
    await ctrl.aio_sleep(1)
```
`_loop()` が通常関数だった場合，スタベーションを避けるため，`_loop()` 呼び出しの間にわずかなディレイ（0.1 秒）が挿入され，また，警告が表示されます．

`_run()` も同様に async である必要があります．
`_run()` が長時間実行される場合は，`ctrl.is_stop_requested()` を監視して，停止要求があったら終了するようにしてください．
（以前のバージョンで使われていた `_halt()` は呼ばれなくなりました．）
```python
async def _run():
    while not ctrl.is_stop_requested():
        ...
        await ctrl.aio_sleep(1)
```

以前のバージョンのスクリプトでよく使われていた，以下のような通常関数の `_loop()` も（警告は出ますが）動作します．
ただし，`ctrl.sleep()` の間はタスク全体が止まり，ブラウザからの関数呼び出しなどの応答が遅れることに注意してください．
```python
def _loop():
    ...
    ctrl.sleep(1)
```

## ブラウザへのデータ送信
SlowTask からブラウザにデータを送る方法としては，データベースに記録してブラウザから読む方法の他に，以下のものがあります．

- **ストリーミング**: SlowTask から値を送り出し，ブラウザでリアルタイムに表示する（push）
- **変数のエクスポート**: SlowTask 中の変数を公開し，ブラウザからの要求に応じて現在の値を返す（pull）
- **コンテンツの動的生成**: HTML やレイアウトの内容を SlowTask で生成する

いずれの場合も，得られるのは「現在」の値のみです．履歴が必要な場合は，データベースに記録してください．

### ストリーミング
ControlSystem の `aio_stream(name:str, value)` メソッド（または `stream(name:str, value)`）を使って，SlowTask スクリプトから値をブラウザに送り，ライブ更新することができます．
```python
from slowpy.mesh import Tasklet
tasklet = Tasklet()

from slowpy.control import control_system as ctrl
V0 = ctrl.ethernet(host, port).scpi().command("V")

@tasklet.loop(interval=1.0)
async def loop():
    await ctrl.aio_stream('V0', await V0.aio_get())   # pushing to consumers
```
ストリーミングできる値の型には，数値，文字列，dict，Python の dataclass，SlowPy のコントロールノード，SlowPy の解析オブジェクト（ヒストグラムなど）があります．
数値や文字列はスカラデータとして，dataclass や dict は Tree 型データとして扱われます．
送られた値は，ブラウザの Data Channels に `current` 型のデータとして表示され，通常のデータと同様にパネルに追加できます．

`stream()` は async でない関数からも使えますが，SlowTask として実行されている（Tasklet のイベントループが走っている）必要があります．
内部では，値は SlowMesh の `data.stream.{name}` トピックに publish されています．

### 変数のエクスポート
ControlSystem の `expose(name:str, obj)` メソッドを使うと，SlowTask 中の変数を公開できます．
公開した変数は，`{タスク名}.{name}` という名前のデータチャンネルとして，データベース中のデータと同様にブラウザからアクセスできます（タイムスタンプが「現時刻」のデータが一点だけ保存されているように見えます）．
ストリーミングが SlowTask からの push なのに対して，エクスポートは，ブラウザからの要求に応じて値を返す pull のインターフェースです．「必要なときに最新値を得る」用途に向いています．

```python
from dataclasses import dataclass

@dataclass
class RunStatus:
    run_number: int = 1
    running: bool = False
run_status = RunStatus()

@tasklet.initialize()
async def initialize():
    ctrl.expose('status', run_status)    # タスク名が run_control なら，チャンネル名は run_control.status
```
エクスポートできるものには，コントロールノード，SlowPy の解析オブジェクト，dict，dataclass などがあります．
`expose()` は，Tasklet が開始した後（initialize コールバックの中など）に呼んでください．

コントロールノードは，`tasklet.mesh.export(name, node)` で直接エクスポートすることもできます．
以下は，ディスク使用量を返すノードを作成してエクスポートする例です．
```python
import shutil
from slowpy.control import ControlNode

class DiskUsageNode(ControlNode):
    async def aio_get(self):
        total, used, free = tuple((int(x*1e-8)/10.0) for x in shutil.disk_usage('.'))
        return { 'tree': { 'total_GB': total, 'used_GB': used, 'free_GB': free } }

tasklet.mesh.export('disk_usage', DiskUsageNode())
```
外部に公開するノードは，必要に応じて `readonly()` などで操作を制限してください．

### フォーム値の読み書き
名前を付けた HTML フォームの入力値は，ControlSystem の `form(name)` ノードを使って SlowTask から読み書きできます．
例えば，ブラウザで最後に入力された値を，タスク開始時の初期値として使ったり，タスク側で決めた値をブラウザのフォームに表示させたりできます．
```python
@tasklet.initialize()
async def initialize():
    # ブラウザのフォーム "pid_setup" の現在の入力値を dict として取得
    form = await ctrl.form('pid_setup').aio_get()
    Kp = form.get('Kp', 1)
    ...

@tasklet.mesh.export()
async def stop():
    ...
    # フォーム "run_control" の "run_number" 入力の表示値を変更
    await ctrl.form('run_control').element('run_number').aio_set(run_status.run_number)
```
`ctrl.form(name).aio_set(dict)` で，複数の入力値をまとめて設定することもできます．

### コンテンツの動的生成
`@tasklet.content(name)` デコレーターにより，通常は SlowDash プロジェクトの `config` 以下に置かれるファイルの内容を動的に生成することができます．
これにより，タスクスクリプトと，それをコントロールするための HTML フォームを一つのファイルにまとめて，整合をとりやすくできます．
```python
@tasklet.content('html-test.html')
def html():
    return '''
      <form name="test">
        Voltage: <input type="number" name="voltage" value="0">
        <button name="test.set_V0()">Set</button>
      </form>
    '''
```
ブラウザからは，HTML ファイル `html-test.html` が `config` に存在するかのように見えます．

HTML パネルで `On Update: Reload HTML` をチェックすると，データ更新のたびにこの関数が呼ばれるので，データを含んだ HTML ページを動的に生成することもできます．
以下は，ディスクの使用量をテーブルに整形して表示する例です．
```python
import shutil

@tasklet.content('html-disk_usage.html')
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

`config/slowplot-XXX.json` も同じように生成できるので，HTML フォームと合わせて，SlowTask から，それを使うための完全なレイアウトを提供することができます．
コンテンツ生成関数は普通の Python 関数なので，Jinja などのテンプレートエンジンを組み合わせて使うこともできます．

## Matplotlib 連携
Matplotlib の Figure は，スクリプトを変更することなく，そのまま SlowDash のレイアウトにストリーミングできます．
```python
import matplotlib.pyplot as plt

async def _loop():
    fig, axes = plt.subplots(2, 2)
    #... draw plots in the usual way

    fig.show()   # this is overriden by SlowDash
    
    await asyncio.sleep(1)
```
SlowDash は `Figure.show()` をオーバーライドして，レイアウトを抽出し，描画図形からヒストグラムやグラフの値を読み取ります．
そして，同じレイアウトの `slowplot-XXX.json` を動的に生成し，データを SlowDash のストリーミングに送り出します．
例のように `Figure.show()` を使う代わりに，`pyplot.show()` や `Figure.savefig(name)` を使っても，SlowDash へのストリーミングが行われます．
（`savefig()` の場合は，通常のファイル保存も行われます．）
生成されるレイアウトの名前は，`Figure.show()` と `Figure.savefig()` ではタスク名，`pyplot.show()` では `{タスク名}.fig{番号}` になります．

SlowTask として実行される場合，Matplotlib の GUI は無効化されます（`Agg` バックエンドが使われます）．

その他の例は `ExampleProjects/Streaming/Matplotlib` にあります．

# SlowMesh
複数の SlowTask スクリプトはネットワーク上に展開でき，SlowMesh の上で通信をしながら，協調して動作することできます．
SlowMesh は，SlowDash サーバーと各 SlowTask の間のメッセージ交換の通信基盤で，以下の通信機能を提供します．

- **PubSub**: トピック名をつけたメッセージの交換（Publish / Subscribe）
- **遠隔関数呼び出し (RPC)**: 他のタスクがエクスポートした関数の呼び出し
- **Registry (Key-Value Store)**: タスク間で共有される名前付きの値置き場

<img src="fig/SlowMeshConcept.png" width="40%">

PubSub では，送信側は受信相手を知らずにメッセージを Publish し，受信側は送信元を知らずに必要なトピックを Subscribe して受信します．
これは，相手の動作・インターフェースを知った上で通信する遠隔関数呼び出しと大きく異なり，要素間の相互依存を大幅に減少させます．
SlowDash では，PubSub を積極的に活用し，「データを読んだら（知らない誰かが処理すると思って）メッシュに投げる」「関連のあるトピックは自分で受信する」「受信データに対して自分の責任を果たす」「処理結果を生成したらメッシュに投げる」というモデルで分散処理を行います．
例えば，「データを読んだら SlowMesh に publish するタスク」「データを受信してデータベースに記録するタスク」「データを受信して解析し，結果を publish するタスク」のように機能を分けると，それぞれのタスクを独立に開発・テスト・再起動できるようになります．

## 基本的な使い方
SlowTask は，Tasklet を介して接続済みの SlowMesh を保持していて，`tasklet.mesh` から各機能を使用できます．

```python
from slowpy.mesh import Tasklet, DataPacket
tasklet = Tasklet()

# データを data.store トピックに publish（DataPacket の引数は DataStore.append() と同じ）
@tasklet.loop(interval=1)
async def read_data():
    volt = float(await device.command('MEAS:VOLT:DC').aio_get())
    await tasklet.mesh.aio_publish(DataPacket(volt, tag='volt').to('data.store'))

# data.store 以下のトピックを subscribe して，データベースに記録
@tasklet.mesh.on('data.store.>')
async def store(data:DataPacket):
    for channel, value in data.values.items():
        datastore.append(value, tag=channel, timestamp=data.timestamp)

# 他のタスクの関数を呼び出す
@tasklet.mesh.export()
async def start():
    await tasklet.mesh.aio_call('histogram.clear')

# レジストリに値を記録・取得
@tasklet.initialize()
async def initialize():
    run_number = await tasklet.mesh.registry.aio_get('setup.run.number', 0)
    await tasklet.mesh.registry.aio_set('setup.run.number', run_number + 1)
```

現時点では，SlowMesh で送受信できる値（publish するデータ，RPC の引数と戻り値，レジストリの値）は，JSON にシリアライズできるものに限られます．

## SlowMesh への接続
### 接続先
SlowMesh への接続は Tasklet が自動で行います．接続先の URL は以下のように決まります．

- SlowDash サーバーから起動された場合：サーバーが `slowdash-task` コマンドの `--mesh` オプションで指定する
- `slowdash-task` コマンドで独立に起動した場合：`--mesh` オプションで指定する
- スクリプトを直接実行した場合：`tasklet.run(mesh_url=...)` で指定する

接続先 URL が与えられない場合は，プロセス内だけで閉じたローカルの PubSub が使われます．
この場合，自分自身が publish したメッセージを自分で subscribe することはできますが，他のタスクとの通信やレジストリの使用はできません．
スクリプト単体の動作確認などに使えます．

### メッセージングバックボーン
SlowMesh は，下位の通信層としてメッセージングバックボーンを使用します．
デフォルトでは，SlowDash サーバーに組み込まれた SlowMQ が使われるので，何も設定せずにそのまま使用できます．
SlowMQ は HTTP(S) 上の WebSockets で実装されていて，SlowDash サーバーの URL（ポート）でそのままアクセスできます．

SlowMQ の代わりに，NATS や MQTT，Redis，RabbitMQ などの広く使われている外部のメッセージングシステムを使うこともできます．
この場合は，`SlowdashProject.yaml` の `mesh` エントリで接続先を指定します．サーバーから起動されるタスクにも同じ URL が渡されます．
```yaml
slowdash_project:
  ...
  mesh:
    url: nats://localhost
```

| バックボーン | URL 形式 | ブローカー | 備考 |
|---|---|---|---|
| SlowMQ | `slowmq://HOST:PORT` (HTTP) または `slowmqs://HOST:PORT` (HTTPS) | 不要 (SlowDash 組み込み) | デフォルト．ファイアウォールを超えてアクセス可能 |
| NATS | `nats://HOST` | 別に NATS サーバーが必要 | |
| MQTT | `mqtt://HOST` | 別に MQTT ブローカー（eclipse-mosquitto など）が必要 | |
| RabbitMQ | `rabbitmq://USER:PASS@HOST/EXCHANGE` | 別に RabbitMQ サーバーが必要 | |
| Redis-PubSub | `redis://HOST/DB` | 別に Redis サーバーが必要 | トピックフィルタに制限あり |

認証情報が必要なら，`HOST` の直前に `USER:PASS@` を挿入してください．

QoS 設定（at-most-once / at-least-once / exactly-once）などは，基本的にはバックボーンのデフォルトが使用されます．
システムの発展に応じてバックボーンを切り替えていくような運用を想定しています（SlowMQ から始めて，性能または機能が足りなくなったら NATS に移行する，など）．
バックボーンを切り替えても，ユーザースクリプトを変更する必要はありません．

メインの SlowMesh とは別に，外部のメッセージングシステムに接続したい場合は，`tasklet.external_mesh(url)` で追加の Mesh オブジェクトを作成できます．
これはメインの Mesh と一緒に開始・終了され，同じ `on()` や `aio_publish()` などのインターフェースで使用できます．

## PubSub
### Publish
```python
# トピック名と値を指定して publish
await tasklet.mesh.aio_publish('mydaq.control.start', {'run_number': 10})

# MeshPacket を publish（トピック名は MeshPacket が決める）
await tasklet.mesh.aio_publish(DataPacket(volt, tag='volt').to('data.store'))
```
`aio_publish()` は async 関数です．async でない関数からは，代わりに `publish()` を使用してください（引数は同じです）．
`publish()` を使う場合も，SlowTask として実行されている（Tasklet のイベントループが走っている）必要があります．

`headers` 引数に dict を渡すと，メッセージにヘッダを付加できます．

### Subscribe
`@tasklet.mesh.on(topic)` デコレーターで，指定したトピックのメッセージを受信したときに呼ばれる関数を指定します．
関数は通常の関数と async 関数のどちらでも構いません．
```python
@tasklet.mesh.on('mydaq.control.start')
async def handle_start(data):
    run_number = data.get('run_number')
    ...
```
関数の引数の数と型アノテーションにより，渡されるものが変わります．

| 関数の形 | 渡されるもの |
|---|---|
| `def handler()` | なし（受信したことだけを知りたい場合） |
| `def handler(data)` | メッセージ本体 |
| `def handler(packet:DataPacket)` | MeshPacket に変換したメッセージ（後述） |
| `def handler(headers, data)` | ヘッダとメッセージ本体．受信したトピック名は `headers['topic']` |

トピックフィルタを使って複数のトピックを受信する場合に，実際のトピック名を知りたいときは，最後の形を使ってください．

実行中に動的に subscribe を追加する場合は，`await tasklet.mesh.aio_subscribe(topic, handler)` を使います．

### トピック名とトピックフィルタ
トピック名は，`data.store.HV.ch01` のように `.` で区切った階層構造にできます．
Subscribe では，以下のトピックフィルタを使用できます（NATS と同じです）．

- `*` は任意の一階層にマッチ
- `>` は任意数の末尾の階層にマッチ（最後の文字としてのみ使用可能）

例えば，`data.store.>` は `data.store` 以下の全てのトピックに，`data.*.HV.ch01` は `data.store.HV.ch01` と `data.stream.HV.ch01` の両方にマッチします．

SlowMQ と NATS 以外のバックボーンを使用した場合，これらの文字はそのバックボーンの文字に置き換えられて渡されます（MQTT では `/`，`+`，`#` など）．
このため，トピック名に `/`，`#`，`+`，`:` などの文字を含めると，バックボーンによっては問題を引き起こします．これらの文字の使用は避けてください．
また，Redis は厳密な階層構造を持たないので，フィルタの動作が近似的になる場合があります．

### トピック名の使用区分
トピック名は SlowDash 全体で予約されていますが，以下のものはユーザーが自由に使用できます．

- 大文字から始まるもの（`KamLAND.control.start` など）
- `my` から始まるもの（`my.>` や `mydaq.>` など）
- `test` から始まるもの（`test.>` や `testdaq.>` など）
- `setup.>`
- `user.>`

SlowDash が使用している主なトピックは以下のとおりです．

| トピック | 内容 | MeshPacket |
|---|---|---|
| `data.store.{channel}` | 記録するデータ（通常，記録用のタスクがデータベースに保存する） | `DataPacket` |
| `data.stream.{channel}` | 表示用のデータ（記録されない） | `DataPacket` |
| `form.{form_name}.{element_name}` | 名前を付けた HTML フォームの入力値 | `FormPacket` |
| `log.{level}.{logger}` | ログメッセージ | |
| `sd.>` | SlowDash の内部使用（タスク管理，RPC など） | |

`data.` で始まるトピックに流れるデータは，SlowDash サーバーがチャンネルごとの最新値を保持していて，ブラウザから `current` データとして表示できます．
前述の `ctrl.stream()` は，`data.stream.{name}` トピックにデータを publish しています．

### MeshPacket
SlowDash が使用するトピックには，メッセージのスキーマ（データ構造）が決められているものがあります．
MeshPacket を使うと，ユーザーのスクリプトがスキーマの詳細に依存せず，メッセージの構築や解読の手間も省けます．

| MeshPacket | 対象トピック | コンストラクタ |
|---|---|---|
| `DataPacket` | `data.*.>` | `DataPacket(values, *, tag=None, timestamp=None)` |
| `FormPacket` | `form.*.>` | `FormPacket(form, element, value)` |

#### DataPacket
`DataPacket` のコンストラクタの引数は `DataStore.append()` と同じです．
つまり，データストアに直接記録するのと，SlowMesh に publish するのは，ほぼ同じ書き方になります．
```python
from slowpy.mesh import DataPacket

temp0 = thermometer.ch(0).get()
await tasklet.mesh.aio_publish(DataPacket(temp0, tag='temp0').to('data.store'))
```
publish するトピックはデフォルトで `data.store.{channel}` で，`data.store` の部分は `to(topic_prefix)` で変更できます（`to('data.stream')` など）．
数値の他，ヒストグラムなどの SlowPy の解析オブジェクトや，Trend の `timeseries()` などの時系列データも送ることができます．

受信側では，ハンドラ関数の引数に `DataPacket` の型アノテーションをつけると，受信したメッセージが DataPacket に変換されて渡されます．
```python
@tasklet.mesh.on('data.>')
async def handle_data(data:DataPacket):
    t = data.timestamp
    for channel, value in data.values.items():
        ...
```
受信した DataPacket の `values` は，チャンネル名をキー，値を値とする dict です．

#### FormPacket
名前を付けた HTML フォームの入力値が変更されると，`form.{form_name}.{element_name}` トピックにメッセージが publish されます．
これを subscribe すれば，ボタンを押す前でも，入力値の変更に即座に反応することができます．
```python
from slowpy.mesh import FormPacket

@tasklet.mesh.on('form.pid_setup.>')
async def handle_form(packet:FormPacket):
    print(packet.form, packet.element, packet.value)
```
逆に，`FormPacket` を publish すると，ブラウザに表示されているフォームの値を変更できます．
通常は，前述の `ctrl.form(name)` ノードを使う方が簡単です．

### PubSub Last-Value Cache
SlowDash サーバーは，PubSub の全トピックを subscribe して，トピックごとの最新のメッセージをレジストリの `pubsub.{トピック名}` に保持しています．
これにより，遅れて開始したタスクが，それまでに publish されたステータス情報などを取得できます．
```python
@tasklet.initialize()
async def initialize():
    # 最後に publish された mydaq.status のメッセージ
    status = await tasklet.mesh.registry.aio_get('pubsub.mydaq.status')
```

## 遠隔関数呼び出し (RPC)
RPC は，ある SlowTask がエクスポートした関数を，他の SlowTask から名前で呼び出すための仕組みです．
ブラウザからの関数呼び出しも，内部では RPC を使っています．

### 呼び出される側
関数のエクスポートについては，前述の「関数のエクスポート」の節を参照してください．
```python
@tasklet.mesh.export()
async def chat(line, *, sender=None):
    print(f'You ("{sender}") sent me "{line}".')
    return str(datetime.datetime.now())
```
戻り値は，JSON にシリアライズできる値である必要があります．
また，前述のとおり，エクスポートした関数は 1 秒程度を目安に return するようにしてください．

### 呼び出す側
```python
return_value = await tasklet.mesh.aio_call('chat_task.chat', line, sender='me')
```

- 最初の引数が `タスク名.関数名` で，それ以降の引数が遠隔関数の引数にそのまま渡されます．
- 引数に渡せるのは，JSON にシリアライズできる値のみです．
- 呼び出し先で例外が発生した場合や，タイムアウトまでに応答がない場合（呼び出し先のタスクが走っていない場合など）は，例外が投げられます．
- デフォルトのタイムアウト時間は 5 秒です．

呼び出しごとにタイムアウト時間を指定する場合は，`aio_call_many()` を使用します．
```python
replies = await tasklet.mesh.aio_call_many('chat_task.chat', [line], {'sender': 'me'}, expected_replies=1, timeout=10, raise_on_timeout=True)
```
`aio_call_many()` は，応答の list を返します．各応答は，以下のようなフィールドを持つ dict です：
```python
{ 'status': 'ok', 'message': 'ok', 'return_value': result }
```
`status` には `ok` の他に `error` と `cancelled` があり，エラーの場合は `message` にエラーメッセージが入ります．

### コントロールノードのリモートアクセス
`tasklet.mesh.export(name, node)` でエクスポートしたコントロールノードは，他のタスクから `remote_node()` を使って，ローカルのノードと同じようにアクセスできます．

呼び出される側（タスク名 `device`）：
```python
from slowpy.control import control_system as ctrl

V0 = ctrl.ethernet('192.168.1.43', 5025).scpi(append_opc=True).command('VOLT')
tasklet.mesh.export('V0', V0.setpoint(limits=(0, 100)))
```

呼び出す側：
```python
V0 = tasklet.mesh.remote_node('device.V0')

await V0.aio_set(10)
print(await V0.aio_get())
```
リモートノードには async 版の `aio_set()` と `aio_get()` のみがあります．

## Registry (Key-Value Store)
Registry は，複数の SlowTask が共有する名前付きの値置き場です．
状態，設定値，処理要求などをタスク間で共有する用途を想定しています．
レジストリのサービスは SlowDash サーバーの中で動いているので，使用するには SlowDash サーバーへの接続が必要です．

### 基本操作
レジストリには，`tasklet.mesh.registry` を経由してアクセスします．
```python
registry = tasklet.mesh.registry

# 値のセット
await registry.aio_set('setup.run.number', run_number)

# 値の取得（キーが存在しない場合はデフォルト値が返される）
run_number = await registry.aio_get('setup.run.number', 0)
```

Registry には，以下のメソッドがあります：

- 書き込み (set)： `aio_set(key, value, *, cas_revision:int|None=None) -> int|None`
- 読み出し (get)： `aio_get(key:str, default=None, *, with_meta:bool=False)`
- キー一覧 (keys)： `aio_keys(prefix:str='', limit:int|None=1000) -> list[str]`
- 削除 (delete)： `aio_delete(key:str, *, cas_revision:int|None=None) -> bool`

### キーと値
**キー**: キーは `.` で区切られる階層構造を持ちます．
各階層の名前には，Python などのプログラミング言語における識別子（変数名など）と同じような名前を使用してください．具体的には，英数字またはアンダースコアだけで構成され，かつ，最初の文字に数字は使用できません．

**値**: 値には，現時点では JSON にシリアライズできる値だけが使用できます．

**使用区分**: キーの名前も SlowDash 全体で予約されていますが，トピック名と同様に，以下のものはユーザーが自由に使用できます．

- 大文字から始まるもの（`KamLAND.>` など）
- `my` から始まるもの（`mydaq.>` など）
- `test` から始まるもの（`testdaq.>` など）
- `setup.>`
- `user.>`

### 階層のグループ化
キーの最後に `>` を付けると，その階層以下のエントリをまとめて一つの dict として扱うことができます．
```python
await registry.aio_set('user', 'slowuser')
await registry.aio_set('state.run.mode', 'physics')
await registry.aio_set('state.run.number', 123)

print(await registry.aio_keys('state.run'))       # -->  ['state.run.mode', 'state.run.number']
print(await registry.aio_get('state.run.mode'))   # -->  physics
print(await registry.aio_get('state.run.>'))      # -->  {'mode': 'physics', 'number': 123}
print(await registry.aio_get('.>'))               # -->  {'user': 'slowuser', 'state': {'run': {'mode': 'physics', 'number': 123}}}
```

`aio_set()` でも，キーの最後に `>` をつけて値に dict を渡すと，その階層以下に dict を展開したエントリを作成します．
つまり，以下の２つは同じ動作をします．
```python
doc = {'run': {'mode': 'physics', 'number': 123 }, 'running': True }
await registry.aio_set('state.>', doc)
```
```python
await registry.aio_set('state.run.mode', 'physics')
await registry.aio_set('state.run.number', 123)
await registry.aio_set('state.running', True)
```

これは，`>` をつけずに dict を値として渡すのとは異なることに注意してください．
以下では，一つのエントリの中に，全体を一つの dict 値として格納しています．
```python
await registry.aio_set('state', doc)
```
どちらの場合でも，`aio_get('state.>')` は同じ結果を返しますが，後者の場合は `state.run.number` というエントリは存在しないので，`aio_get('state.run.number')` はデフォルト値を返します．
普段は `>` をつけて展開して保存する方がトラブルが少ないですが，配列を含んだ dict などを記録する場合には，展開しない保存が必要になります．

ある階層に値を記録し，さらにその下の階層にも値を記録すると，グループ化して取得したときに，その階層の値は `$value` というフィールドに入ります．
（一つのノードが値と子ノードの両方をもつことは，dict や JSON では表現できないためです．）
```python
await registry.aio_set('state.run', 'running')
print(await registry.aio_get('state.run.>'))      # -->  {'mode': 'physics', 'number': 123, '$value': 'running'}
```
混乱を避けるため，子ノードがある階層には値を記録しないようにしてください．この例では，`state.run` の代わりに `state.run.status` などに記録すれば問題を回避できます．

### Compare-And-Set (CAS)
Registry では，他のタスクが書いたものを意図せず上書きすることを防ぐため，Compare-And-Set (CAS) オプションを備えています．

- 各エントリには，書き込み回数を数える CAS リビジョンが割り当てられる
- `aio_set()` は CAS リビジョンをインクリメントし，新しい CAS リビジョンを返す
- `aio_set()` の `cas_revision` オプションが None でない場合，その値が保持されている CAS リビジョンと一致しないと，書き込みに失敗する
- `aio_delete()` も同様に，CAS リビジョンが一致しなければ削除に失敗する

これにより，自分が設定した値を他の誰かが書き換えた場合に，それを知らずに上書きすることを避けられます．

`aio_get()` の `with_meta` オプションを `True` にすると，値の代わりに，CAS リビジョンや書き込み時刻を含んだメタデータが返されます：
```python
{
    "key": キー,
    "value": 値,
    "revision": CAS リビジョン,
    "updated": 最終書き込み時刻
}
```

### 永続化
レジストリの値は，通常は SlowDash サーバーのメモリ上にのみ保持され，サーバーを再起動すると失われます．
一部のエントリは，書き込みのたびにプロジェクトディレクトリのファイル（`registry-{パス}.json`）に保存され，次にサーバーが開始したときに自動で読み込まれます．
現時点では，名前を付けた HTML フォームの入力値（`pubsub.form.>`）のみが永続化の対象です．

### ブラウザからのアクセス
レジストリに記録された値は，データベース中のデータと同じようにブラウザから表示できます．
データチャンネル名に `@registry:{キー}` を指定してください（例えば `@registry:setup.run.number`，階層全体を Tree として表示するには `@registry:setup.run.>`）．

また，Web API からもアクセスできます．
```console
$ curl http://localhost:18881/api/registry/value/setup.run.number
```

## 標準入出力とログの転送
SlowTask の中で `print()` などにより標準出力・標準エラー出力に書いたメッセージは，SlowMesh に publish され，SlowDash のホーム画面のコンソールに表示されます．
（ローカルの標準出力にも書き出されます．）
この転送が不要な場合は，`Tasklet(use_mesh_stdio=False)` としてください．

Python の標準の `logging` に書いたメッセージも，SlowMesh の `log.{レベル}.{ロガー名}` トピックに転送されます．

## 使用例
SlowMesh を使って SlowTask を読み出し・記録・解析の機能ごとに分離する例が，[Quick Tour](QuickTour.html) にあります．
