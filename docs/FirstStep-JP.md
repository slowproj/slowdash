---
title: SlowDash を使ってみる
---

# SlowDash とは
スローコントロールのダッシュボードを Grafana で作らされた経験に基づいて開発が開始されました．おおまかには，

- Grafana みたいに，データベース上にあるデータ（主に時系列）をリアルタイムにビジュアライズする
- LabVIEW のパネルみたいに，画面上にいろいろ並べて，デバイスの状態を一覧表示したり，マウス等で操作したりする
- ROOT みたいなデータ型（ヒストグラムとか誤差つきグラフとか）を直接扱う
- Jyputer に接続して収集中のデータを対話的に解析する
- Python スクリプトを組み込んで機器制御やリアルタイム処理をする

ための Web ベースのソフトウェアです．ブラウザ側の JavaScript と，サーバー側の Python で構成されています．

もともとはスローコントロール用でしたが，現在では物理実験に関わる全てのデータのビジュアライズと，DAQ を含むシステムコントロールの UI を目指して開発をしています．現時点で，Grafana で行うようなビジュアライゼーションの部分はほぼ実装済みで，解析およびコントロールの部分が開発中です．

データベースアクセス以外は外部ライブラリを使っておらず，ソフトウェアの寿命が外のライブラリの変更等に影響されることはないようになっています．特に，流行り廃れが激しい JavaScript の部分はフレームワークなどは使わず，完全に自己完結です（使っていたけど排除しました）．データベース側および解析モジュールは，全て独立なプラグインとなっており，いつでも切り捨てられます．依存性がないので，インストールがとても楽で，使用後も痕跡を残さずきれいに削除できます．それでもインストールをしたくない人のために，すぐに使える Docker コンテナも提供されています．

<img src="fig/Gallery-ATDS-Dashboard.png" style="width:40%;box-shadow:0px 0px 15px -5px rgba(0,0,0,0.7);">
<img src="fig/Gallery-RGA.png" style="width:40%;box-shadow:0px 0px 15px -5px rgba(0,0,0,0.7);">

### 機能と特長（予定を含む）

Grafana と似たビジュアライゼーション（ほぼ実装済み）

- 実時間で更新していくプロットと，過去のデータの表示
- 物理実験で使われているデータベースはだいたい使える．なくてもプラグインで追加は簡単．
  - SQL データベース: PostgreSQL, MySQL, SQLite
  - 時系列データベース： InfluxDB
  - キーバリューストア： Redis
  - ドキュメントデータベース： MongoDB, CouchDB
- 実験ですでに使われているいろいろなデータ形式（スキーマ）に，時系列データならほぼ全て対応できる．
- 誰でもブラウザから対話的にプロットを構成できる．作ったものは保存して共有できる．

Grafana と違って，物理屋に使いやすいようになっています（ほぼ実装済み）:

- ズームや表示範囲の変更が簡単
- 対数軸への切り替えが簡単
- 新しいプロットをすぐに作れる
- URL からプロットを構成できる &rarr; いろんなプロットへのリンクをたくさん作れる
- ヒストグラムやエラーバー付きグラフも直接サポート
- 時系列以外のデータも普通に扱える
- 何も考えずに長期間のデータを表示してもブラウザがデータを溜め込まない
- 表示範囲のデータを簡単に CSV  等でダウンロードできる
- 表示プロットを Jypyter にエクスポートして解析を継続できる

さらに，コントロール用の機能も実装しています（８割くらい完成）:

- サーバー側にユーザの Python コードを置いて，ブラウザからコマンドを送れる
- サーバー側のユーザ Python コードが動的に生成したデータもストリーミング表示できる
- ブラウザ上でも簡単なデータ加工が行える
- ユーザ作成の任意の HTML コードを組み込める

将来的には，

- サーバー側での継続的データ処理とアラーム
- データベース以外からのデータのビジュアライズ（ROOT ファイルとか，どっかのストリーミングとか）
- ヒストグラムのフィティング等まで含めた埋め込みおよび対話的データ解析
- メッセージングシステムへの直接接続 (AMQP とか Kafka とか)

Grafana にあって今の SlowDash にないもの（将来は実装されるかも）：

- 柔軟なレイアウト構成
- 円グラフ，重ね棒グラフ，みんな使ってる丸いゲージ，Excel によくあるチャート，...
- 地理データ表示（世界地図を塗り分けるとか；SlowDash でもできるけど地図がない）
- データベース等の設定ファイルのブラウザからの構築
- ユーザ管理，アクセス管理

実験でよく使われるけど，今の SlowDash にないもの：

- ３次元の絵
- トラックとかを描くイベントディスプレイ（描画要素の数が毎回変わるもの）

JSROOT や Streamlit，Bokeh との違い：

- SlowDash と Grafana にあるけど JSROOT/Streamlit/Bokeh にない機能
  - コーディングなし：マウス数回のクリックでデータベース上のデータを可視化
  - データを見るユーザが自分でブラウザ上でプロットを作成し，保存・共有できる
- SlowDash と LabVIEW UI にあるけど JSROOT/Bokeh にない機能
  - 装置の構成図の上にデータを表示して，デバイスを操作できる
  - たくさんのユーザ入力を受け取るフォームを作れる
- 数値データでなくても良い．ログメッセージとか，ステータス一覧とか，写真とか

- JSROOT や Bokeh でできて，今の SlowDash にないけど，やりたいこと（できる気がするもの）
  - 動いている ROOT の中身をリアルタイムにビジュアライズ
  - Jupyter でブラウザからサーバー側の解析コードを書いて，テストして，そのままデプロイ
  - (動いている Python/Matplotlib の中身(Figure)を抜き出してリアルタイムにビジュアライズすることはすでにできます）


### よくある宣伝
みんな書いているので，いちおう書いておきます．

- MVC アーキテクチャに基づいています．
- Web API は全て RESTful です．
- UI はレスポンシブです．
- プラグインで機能拡張できます．
- クラウドネイティブな設計です．
- オープンソースです．
- 最新のユーザー体験を提供します．
- 高度なデータ統合で DX を推進します．


#  インストール
### サーバー側動作環境
#### Docker
Docker があれば，DockerHub または GitHub CR にある SlowDash のイメージがすぐに利用できます (Linux / Windows WSL / MacOS)．

- Docker Hub: [https://hub.docker.com/r/slowproj/slowdash](https://hub.docker.com/r/slowproj/slowdash)
- GitHub CR: [https://github.com/slowproj/slowdash/pkgs/container/slowdash](https://github.com/slowproj/slowdash/pkgs/container/slowdash)

ただ，最初から Docker を使うと設定ファイルの扱いなどが面倒だと思います．ここでは，Docker を使う手順を最後に解説します．

#### 標準インストール
基本的に Python 3 が動けばすぐ使えます．

- UNIX 風の OS．Ubuntu で開発，macOS とか Windows の WSL でも動いた．WinPython でも動くらしい．
- Python 3.9 以上と venv

ここでのインストールでは，venv を使用してそこに必要なパッケージを自動インストールするので，手動で Python のパッケージなどを準備する必要はありません．(venv を使わずにインストールすることもできます．) 

### ウェブブラウザ
Firefox で開発していて，たまに Chrome と Edge と Safari でテストしています．タブレットや携帯などのモバイルデバイス上でもそこそこ動作します（プロットの移動やズームは二本指です）．


### ダウンロード
GitHub からダウンロードできます． サブモジュールを使っているので，`--recurse-submodules` オプションをつけてください．
```console
$ git clone https://github.com/slowproj/slowdash.git --recurse-submodules
```
(`git` コマンドが利用できない場合，[github のページ](https://github.com/slowproj/slowdash) からパッケージをダウンロードすることもできます．）

これで，`slowdash` というディレクトリが作成されます．インストールおよび次の Quick Tour では，全てのファイルは slowdash のディレクトリ以下に作られるので，この過程でユーザのシステムが汚されることはありません．また，このディレクトリを削除すれば，全てをなかったことにできます．

### ドキュメント
公式ドキュメントは，展開したディレクトリの `docs` 以下にあります．`index.html` をブラウザで開いてください．
```console
$ firefox slowdash/docs/index.html
```
（macOS 等では，`firefox` コマンドを直接実行するのではなく，`open` コマンドを介するようです．）

日本語の隠しドキュメントは `FirstStep-JP.html` です．今読んでいるものですが，`docs` から読むと内部リンクが切れていません．
```console
$ firefox slowdash/docs/FirstStep-JP.html
```

### インストール 

```console
$ cd slowdash
$ make
```
これで，Python 周りのセットアップと，作成した venv へのパッケージのインストールを行います．

venv を使わない場合は，最後の `make` の代わりに `make without-venv` としてください．もし間違えて `make` してしまった場合は，`slowdash` ディレクトリの下にある `venv` ディレクトリを削除すれば同じになります．SlowDash の実行に必要なパッケージの `requirements.txt` ファイルも自動生成されるので，venv を使わない場合はこれを手動でインストールしてください（`pip install -r requirements.txt`）．

以上により，`slowdash/bin`  の下にシェルの設定するスクリプト `slowdash-bashrc` ができるので，これを `source`  してください．
```console
$ source PATH/TO/SLOWDASH/bin/slowdash-bashrc
```
ちなみに中身はこんな感じです．
```bash
export SLOWDASH_DIR=/PATH/TO/SLOWDASH
alias slowdash="$SLOWDASH_DIR/bin/slowdash"
alias slowdash-activate-venv="source $SLOWDASH_DIR/venv/bin/activate"
```
設定ファイルの `source` は，新しいターミナルを開くたびに毎回必要です．
SlowDash を継続的に使うなら，上記の source コマンドを `.bashrc` (Mac では `.zshrc`) などに書いておくと毎回やる必要がなくなります．なお，複数のバージョンの SlowDash インストールを使い分けるなら，上記の source だけで全てを切り替えることができます．

インストールが成功したかは，`slowdash` コマンドを実行してチェックできます．
(`slowdash` コマンドは `slowdash/bin` の下にあります）
```console
$ slowdash
Running in venv at /PATH/TO/SLOWDASH/venv
usage: 
  Web-Server Mode:      slowdash.py [Options] --port=PORT
  Command-line Mode:    slowdash.py [Options] COMMAND

Slowdash Version 250128 "Skykomish"

positional arguments:
  COMMAND               API query string. Ex) "config", "channels", "data/CHANNELS?length=LENGTH"

options:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  port number for web connection; command-line mode without this option
  --project-dir PROJECT_DIR
                        project directory (default: current dir if not specified by SLOWDASH_PROJECT environmental
                        variable)
...
```

任意のポート番号を指定して `slowdash` コマンドを実行し，ブラウザとの接続を確認してください．ここで，プロジェクトがないという警告が出ますが，今はこのまま先に進みます．
```console
$ slowdash --port=18881
23-05-15 20:12:35 WARNING: unable to find Slowdash Project Dir: specify it with the --project-dir option, set the SLOWDASH_PROJECT environmental variable, or run the slowdash commands at a project directory
listening at port 18881
```
```console
$ firefox http://localhost:18881
```

成功すれば以下のようなエラーメッセージが表示されます．

<img src="fig/QuickTour-Welcome.png" style="width:40%">

確認したら，`Ctrl-c` で `slowdash` コマンドを終了してください．

### アップデート
アップデートは，`make` で行うのが簡単です．
```console
$ cd PATH/TO/SLOWDASH
$ make update
```
あるいは，以下のように手動で行っても構いませんが，`--recurse-submodules` をつけるのを忘れないようにしてください：
```console
$ cd PATH/TO/SLOWDASH
$ git pull --recurse-submodules
$ make
```

アップデート直後は，ブラウザのキャッシュに古いスクリプトが残っていることがあります．動作がおかしい場合は，`Ctrl`-`F5` など（ブラウザにより微妙に異なる）で強制リロードを行ってください．（状況が許すなら，キャッシュの全削除をするのが確実です．すいません．この問題はいずれちゃんと対応します．）

# ダミーデータで UI を動かしてみる
ダミーデータを使って SlowDash の UI をテストするプロジェクトがあるので，これを使ってとりあえず動かしてみます．展開した SlowDash ディレクトリの下にある `ExampleProjects` の `DummyDataSource` に `cd` して，そこから `slowdash` を走らせてください．
```console
$ cd PATH/TO/SLOWDASH/ExampleProjects/DummyDataSource
$ slowdash --port=18881
```

プラウザを立ち上げて `http://localhost:18881` に接続すると作成済みページの一覧が表示されます．右上の SlowPlot にある `demo` をクリックすると，以下のようなプロットのデモページが表示されます．データに意味はなく，更新するたびに中身が変わりますが，SlowDash の表示要素の操作を一通り試してみることができます．

<img src="fig/QuickTour-DummyDataSource.png" style="width:40%">

# Quick Tour をやってみる
ここでは，公式ドキュメントの Quick Tour の前半くらい，時系列データのプロットを作るところまでやってみます．

テスト用のデータストアには，SQLite を使います．これは，追加のライブラリをインストールせずに使用でき，また，データがファイルに保存されるため，使用後のクリーンアップが簡単なためです．

最初に，プロジェクト用のディレクトリを作成してください．ディレクトリを作る場所はどこでもいいです．このプロジェクトで作成されるファイルは全てこのディレクトリ以下に格納されます．プロジェクト終了後はディレクトリをまるごと削除しても大丈夫です．途中でプロジェクトディレクトリを別の場所へ移動することも可能です．
```console
$ mkdir QuickTour
$ cd QuickTour
```

### 準備：SlowPy ライブラリを使ってテスト用のデータストアを作る
SlowPy は，SlowDash に含まれる Python のユーザライブラリ部分です．上記のインストールで，`source slowdash/bin/slowdash-bashrc` をしていれば，`slowdash-activate-venv` で SlowDash の venv に入れます（手動で activate しても構いません）．
```console
$ slowdash-activate-venv       (または source PATH/TO/SLOWDASH/venv/bin/activate)
```
インストール時に venv を使わなかった場合 (`pip install -r requrements.txt`した場合)は，この手順は必要ありません．venv から抜ける場合は，端末を閉じるか，`deactivate` コマンドを使ってください．

SlowPy を使って，一秒ごとに乱数の値を SQLite に書き込むスクリプトを作成します．
```python
from slowpy.control import ControlSystem, RandomWalkDevice
from slowpy.store import DataStore_SQLite, LongTableFormat

class TestDataFormat(LongTableFormat):
    schema_numeric = '(datetime DATETIME, timestamp INTEGER, channel VARCHAR(100), value REAL, PRIMARY KEY(timestamp, channel))'
    def insert_numeric_data(self, cur, timestamp, channel, value):
        cur.execute(f'INSERT INTO {self.table} VALUES(CURRENT_TIMESTAMP,%d,?,%f)' % (timestamp, value), (channel,))

ctrl = ControlSystem()
device = RandomWalkDevice(n=4)
datastore = DataStore_SQLite('sqlite:///QuickTourTestData.db', table="testdata", table_format=TestDataFormat())

def _loop():
    for ch in range(4):
        data = device.read(ch)
        datastore.append(data, tag="ch%02d"%ch)
    ctrl.sleep(1)
    
def _finalize():
    datastore.close()
    
if __name__ == '__main__':
    ctrl.stop_by_signal()
    while not ctrl.is_stop_requested():
        _loop()
    _finalize()
```
このスクリプトの詳細は公式ドキュメントの [Controls セクション](ControlsScript.html)に説明があります．ここでは，上記の内容をコピペして，`generate-testdata.py`  というファイル名でプロジェクトディレクトリに保存してください．

このスクリプトを走らせると，テスト用のデータファイルが生成されます．
```console
$ python generate-testdata.py
```
（もしコピペに失敗してエラーが出るようであれば，同じ内容のファイルが `slowdash/ExampleProjects/QuickTour/config/slowtask-testdata.py` にあります．）

10 秒くらい経過したら `Ctrl`-`c` で止めて，できたファイルを確認してください．
```console
$ ls -l
-rw-r--r-- 1 sanshiro sanshiro 24576 Apr 11 16:52 QuickTourTestData.db
-rwxr-xr-x 1 sanshiro sanshiro  3562 Apr 11 16:51 generate-testdata.py
```

データの中身は `sqlite3` コマンドで確認できます．（このコマンドがインストールされてなければ，この手順は飛ばしていいです．）
```console
$ sqlite3 QuickTourTestData.db 
SQLite version 3.31.1 2020-01-27 19:55:54
Enter ".help" for usage hints.
sqlite> .table
testdata
sqlite> .schema testdata
CREATE TABLE testdata(datetime DATETIME, timestamp INTEGER, channel VARCHAR(100), value REAL, PRIMARY KEY(timestamp, channel));
sqlite> select * from testdata limit 10;
2023-04-11 23:52:13|1681257133|ch00|0.187859
2023-04-11 23:52:13|1681257133|ch01|-0.418021
2023-04-11 23:52:13|1681257133|ch02|0.482607
2023-04-11 23:52:13|1681257133|ch03|1.733749
...
```

`sqlite3` の `.schema` コマンド出力にあるとおり，データは `testdata` というテーブルに保存されていて，その構造は以下のようになっています．
```
testdata(datetime DATETIME, timestamp INTEGER, channel VARCHAR(100), value REAL, PRIMARY KEY(timestamp, channel))
```

テスト目的のために，データのタイムスタンプは日付時刻型（SQLite では ISO 表記の文字列）のものと，整数の UNIX 時間の両方が入っていますが，通常はどちらか一方のことが多いと思います．SQLite では，タイムゾーンの扱いに罠が多いので，UNIX 時間の方がいいかもしれません．

データの中身はこんな感じです:

|datetime (DATETIME/TEXT)|timestamp (INTEGER)|channel (VARCHAR(100))|value (REAL)|
|----|-----|-----|-----|
|2023-04-11 23:52:13|1681257133|ch00|0.187859|
|2023-04-11 23:52:13|1681257133|ch01|-0.418021|
|2023-04-11 23:52:13|1681257133|ch02|0.482607|
|2023-04-11 23:52:13|1681257133|ch03|1.733749|
|...||||

ここでは，面倒な例として，日付時刻型のデータにタイムゾーンを明示しないで UTC 時刻を使用しています（SQLite ではこれがデフォルトの関数が多いです）．通常は，タイムゾーン付きまたは UNIX 時間を使用してください．

時系列データのテーブルは，必ずしもこの形になっている必要はありません．特に，テーブルにカラムを追加するのが簡単なタイプのデータストアを使用している場合は，各チャンネルを各カラムにするのも普通にアリだと思います．同時に読み出したデータのグルーピングが簡単になるというメリットもあります．詳しくは，公式ドキュメントの [Data Binding](DataBinding.html) の章を参照してください．

### プロジェクト設定
SlowDash のプロジェクトでは，通常，専用のディレクトリを作って，そこに `SlowdashProject.yaml` という名前のプロジェクト設定ファイルを置きます．（データファイルを直接読む場合などの例外はあります．）どこのデータベースからどのようなデータを読むかなどを，このプロジェクト設定ファイルに記述します．

プロジェクトディレクトリに，以下の内容で `SlowdashProject.yaml` という名前のファイルを作成してください．
```yaml
slowdash_project:
  name: QuickTour   (なんでも良いが，スペースや特殊文字を含まない方が人生が楽になる)
  title: SlowDash Quick Tour  （なんでも良いが，改行や極悪な文字は含まない方がいいと思う）
  
  data_source:
    type: SQLite
    file: QuickTourTestData.db
    time_series:
      schema: testdata[channel]@timestamp(unix)=value
```

`schema` のところで，データのテーブル名と，どの情報がどのカラムに書かれているかを記述しています．フォーマットは，`テーブル名 [チャンネル情報のカラム名] @ 時刻情報のカラム名（時刻の表現形式）= データ値のカラム名` みたいな感じです．詳しくは，[DataBinding](DataBinding.html) の章を参照してください．

この例では，時刻情報に，UNIX タイムスタンプの方を使っています．DateTime 型の方の時刻情報を使う場合は，`schema` の記述を以下のようにしてください：
```yaml
      time_series:
        schema: testdata[channel]@datetime(unspecified utc)=value
```
ここでは，UTC 時刻がタイムゾーン指定なしで使われている悪い例に対応するために，時刻表現形式を `unspecified utc` (「書いてないけど UTC だよ」)と伝えています．保存されているデータがちゃんとタイムゾーン付きの場合は `with timezone` または `aware` を，最悪のケースでタイムゾーンなしでローカルタイムが使われている場合は `without timezone` または `naive` と書いてください．この情報は，SlowDash がクエリを構築する際に，データと同じ時刻表現を使用するために使われます．タイムゾーンを明示しないでローカルタイムを使った場合の惨事が多数報告されているので，新しく作るデータで `without timezone` を選択する理由はないです．（日本国内だけなら関係ないと思ってすでにそういう形式でデータを取ってる場合は，夏時間の導入に反対しておいた方がいいです．）

`slowdash config` コマンドで設定情報の一部が表示されるので，設定ファイルが読めているかのチェックができます．これは，`SlowdashProject.yaml` ファイルを作成したプロジェクトディレクトリで実行してください．
```console
$ slowdash config
{
    "project": {
        "name": "QuickTour",
        "title": "SlowDash Quick Tour",
        "error_message": ""
    },
    "data_source_module": [
        "datasource_SQLite.py"
    ],
    "user_module": [],
    "style": null
}
```

データベースに正しくアクセスできる場合，`slowdash channels` コマンドでチャンネルの一覧を表示できます．
```console
$ slowdash channels
[
  {"name": "ch00"}, {"name": "ch01"}, {"name": "ch02"}, ...
]
```

データの中身は，`slowdash data/CHANNEL` コマンドで見ることができます．
```console
$ slowdash "data/ch00?length=10"
{
  "ch00": {
    "start": 1680223465, "length": 10, 
    "t": [0.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0], 
    "x": [5.180761, 5.92074, 5.515459, 4.883299, 5.650556, 4.284527, 3.884656, 3.223627, 2.06343]
  }
}
```
もう気づいたかもしれませんが，`slowdash` コマンドの第１引数は HTTP でアクセスした場合の URL で，出力はそのリプライです．

### サーバーを走らせる
SlowDash にネットワークからアクセスするために，`--port` オプションで適当なポート番号を指定します．これで，コマンドを HTTP 経由で受け取るようになります．
```console
$ slowdash --port=18881
```
SlowDash を走らせたままブラウザを立ち上げ，使ったポートに接続してください．
```console
$ firefox http://localhost:18881
```

今回はプロジェクト付きで走らせているので，以下のようなスタートページが表示されるはずです．

<img src="fig/QuickTour-Home.png" style="width:40%">

テスト用のデータベースにデータを継続的に記録するため，別ターミナルで先程のデータ生成プログラムを走らせてください．
```console
(別ターミナルを開く)
$ cd PATH/TO/MySlowDashProject
$ slowdash-activate-venv
$ python ./generate-testdata.py
```
データサイズは一時間で 5MB 程度なので，しばらくは走らせ続けて大丈夫です．データファイル（`QuickTourTestData.db`）は，SlowDash が走ってなければ，いつ消しても構いません．またデータが欲しくなったら，再度 `generate-testdata.py` を走らせてください．（データファルを削除せずに走らせても問題ありません．複数同時に走らせたら変なことになると思います．）

プログラムの終了は，全て `Ctrl`-`c` です．それなりに上品に止まります．だめだったら，`Ctrl`-`\` を使ってください．


### ブラウザでデータを見る
ブラウザ上の青い文字のところをクリックすればいろいろとプロットを作成できます．上部の紫色は，東北大学とワシントン大学の共通テーマカラーですが，嫌ならプロジェクト設定ファイルで変更できます．[Project Setup の章](ProjectSetup.html#styles)に説明があります．

右下の Tools にある New Plot Layout で新しい空のページを作ります．その中で，`Add a New Panel` を選んで，`Time-Axis Plot` を選んで，プロットを作成していきます．たぶん自明です．

左上の Channel List のチャンネル名をクリックすると，直近の時系列データのプロットを含んだページが作成されます．それを元にいろいろ追加していくこともできます．

ここまでの準備では時系列データしか生成していないので，すぐにできるのは，それを直接プロットする `Time-Axis Plot (Time-Series)` と，値分布のヒストグラムを作る `XY Plot (Histograms and Graphs)` &rarr; `Histogram of Time-Series Values` です．
以下の章では，ユーザの解析スクリプトなどでヒストグラムやグラフなどを作成し，それらも表示するようにしてみます．


### デバイスからデータを読む
SlowDash は，ウェブサーバとブラウザからなるアプリ部分と，ユーザの Python スクリプトで利用するライブラリ部分から構成されます．
上記のダミーデータ作成では，このライブラリ (SlowPy) を使用しました．アプリとライブラリは融合して動作しますが，それぞれを単体で使用することもできます．
この章では，SlowPy ライブラリを単体で使用してデバイスからデータを読んで，ダミーデータ生成と置き換えます．

#### 準備
SlowPy は SlowDash インストール時に一緒にインストールされますが，標準インストールでは venv の中に入るので，最初にこの venv を有効にしておいてください．
```console
$ slowdash-activate-venv
```
これは新しいターミナルを開くごとに必要です．もし SlowDash 専用のコンピュータを使っているなら，`.bashrc` などの中に以下の行を追加すれば毎回行う必要がなくなります．
```bash
source $SLOWDASH_DIR/venv/bin/activate
```

#### 対象デバイス
ここでは，ネットワーク制御が可能な広く使われているベントトップ型電圧計（マルチメータ）から直流電圧を読み出す例を作成します．
多くの電圧計が同じコマンドを使いますが，特に以下のものは確認してあります（ChatGPT 調べ，2025年8月）：

|メーカー | モデル |
|--------|-------|
| Keysight (Agilent) | 34460A TrueVolt DMM |
| Tektronics / Keithley | DMM6500 |
| Rigol | DM3058 |
| BK Precision | 5492B DMM |

また，多くの電源モジュールも，出力電圧の読み出しで同じコマンドを使用します．なので，この例で同様に使用できます．
以下は確認済のモデルです（ChatGPT 調べ，2025年8月）

|メーカー | モデル |
|--------|-------|
| Keysight (Agilent) | E363x/E364x |
| Tektronics / Keithley | 2230G/2231A |
| Rigol | DP800, DP2000 |
| BK Precision | 9180/9190 |

これらのデバイスは全てイーサーネット経由でコントロールできるものです．
次の手順に進む前に，ネットワークに接続し，電源を入れて，IP アドレス（と念の為ポート番号；マニュアルに書いてあります）を確認しておいてください．

#### 使えるデバイスがない場合
ChatGPT によると，ほとんどの電圧計と電源ユニットでは，ここで使うレベルのコマンドは共通らしいです．
もしいずれのデバイスも利用できない場合は，SlowDash にシミュレータがあるので，代わりにこれを使用して例を実行することができます．
新しいターミナルを開いて，以下のコマンドを実行してください．

```console
$ slowdash-activate-venv
$ cd PATH/TO/SLOWDASH/utils
$ python ./dummy-scpi.py
listening at 172.26.0.1:5025
line terminator is: x0d
type Ctrl-c to stop
```

これで，このデバイスがネットワーク上にあるように振る舞います．使われる IP アドレスはローカルホストのものです．
終了は Ctrl-c を押してください．

#### デバイスからの読み出し
上記のデバイスは全て，SCPI と呼ばれる単純なテキストコマンド体系を使用します．
以下は，ここで使う SCPI コマンドです．

|動作 | コマンド | 戻り値例 |
|----|---------|-------|
| デバイスIDの取得 | `*IDN?`  | `xxxx` みたいな感じ |
| 設定リセット | `*RST`  | たぶんなし |
| DC 電圧値の読み出し | `MEAS:VOLT:DC?` | `2.2` みたいな感じ |

SlowPy ライブラリでは，デバイスの論理構造を反映させたツリーをまず構築します．
この例では，[測定システム] -> [イーサーネット] -> [SCPI デバイス] -> [各コマンド] のような形をしています．
そして，それぞれのツリーのノードに対して値の読み書きを `set(value)` または `value=get()` により行います．

以下は，SlowPy を使用して，上記のデバイスからデバイスIDを取得して表示する完全なコードです．
```python
# SlowPy ライブラリの import
from slowpy.control import control_system as ctrl

# デバイスツリーの構築
device = ctrl.ethernet('172.26.0.1', 5025).scpi()

# "*IDN?" コマンドノードからの読み出し
print(device.command('*IDN?').get())
```
デバイスのアドレスとポート番号は適宜書き換えてください．
この時点でデバイスとの接続確認ができます．

```console
$ slowdash-activate-venv
$ python read-my.py
XXXX
```

以下は，最初に設定リセットをして，1 秒ごとのデータ読み出しを永遠に続ける完全な例です．
```python
from slowpy.control import control_system as ctrl
device = ctrl.ethernet('172.26.0.1', 5025).scpi()

device.command('*RST').set()

import time
while True:
    volt = device.command('MEAS:VOLT:DC?').get()

    print(volt)
    time.sleep(1)
```

SlowPy はデータベース読み書きの機能も提供しています．
以下は，上記の画面への print の代わりにデータベース（この例では SQLite）に記録する完全な例です．
```python
from slowpy.control import control_system as ctrl
device = ctrl.ethernet('172.26.0.1', 5025).scpi()

from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///TestData.db', table="slowdata")

device.command('*RST').set()

import time
while True:
    volt = device.command('MEAS:VOLT:DC?').get()

    datastore.append({'volt': volt})
    time.sleep(1)
```

これをダミーデータ生成プログラムの代わりに走らせれば，実データに対して SlowDash を使えるようになります．
この時点では，停止に `Ctrl-c` または `Ctrl-\` が必要です．
見苦しいことになると思いますが，実害はないはずです．

#### 読み出しスクリプトを SlowDash アプリに統合する
任意の Python スクリプト(SlowPyを使う必要もない)を SlowDash プロジェクトディレクトリの下の `config` ディレクトリ（すでに自動作成されているはず）に `slowtask-XXX.py` という名前で保存すると，SlowDash ホーム画面の左下の "SlowTask" セクションに作成したスクリプトが表示され，コントロールできるようになります．
`SlowdashProject.yaml` の設定で，スクリプトを自動開始するようにしたり，ブラウザからこの Python ファイルを直接編集できるようにすることもできます．具体的な手順は，公式ドキュメントを参照してください．

ただし，上記のスクリプトは，（上品に）停止させるためのコードがありません．アプリ側から停止や再実行をできるようにするためには，アプリからのコントロールを受けられるようにする必要があります．そのために，以下のように SlowDash で規定されているコールバックを実装します．

```python
from slowpy.control import control_system as ctrl
device = ctrl.ethernet('172.26.0.1', 5025).scpi()

from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///QuickTourTestData.db', table="testdata")

device.command('*RST').set()

import time
def _loop():
    volt = device.command('MEAS:VOLT:DC?').get()

    datastore.append({'volt': volt})
    time.sleep(1)
```
`while True` を `def _loop()` に置き換えただけです．
`_loop()` 関数は，SlowDash が実行中（または SlowDash がスクリプトを実行中）に繰り返し呼び出されます．


最後に以下のブロックを追加すると，このスクリプトを単体実行できるようになります．
```python
if __name__ == '__main__':
    while True:
      _loop()
```

さらにひと手間かけて，以下のようにすると Ctrl-c で上品に止まるようになります．
```python
if __name__ == '__main__':
    ctrl.stop_by_signal()
    while not ctrl.is_stop_requested():
        _loop()
```



#### 追加の詳細
電源ユニットを使用する場合で，出力電圧を設定するには以下のようにします．
```python
from slowpy.control import control_system as ctrl
device = ctrl.ethernet('172.26.0.1', 5025).scpi(append_opc=True)

device.command('VOLT').set(3.0)    # this will send "VOLT 3.0; *OPC?"
device.command('OUTP').set('ON')   # this will send "OUTP ON; *OPC?"
```
SlowPy では，全てのコマンドに戻り値があることを期待するので，戻り値のないコマンドが存在するようなデバイスでは，コマンドの完了を待ってそのステータスをかえすコマンド `*OPC?` を付加する必要があります．常に戻り値があるようなデバイスに `*OPC?` を付加しても，通常は無害です．
上記の例では，全ての set() に `*OPC*` を付加するように，`scpi()` ノード自体にオプションを設定しています．
（もともと戻り値のある get() には付加されません．）
もしコマンドごとに切り替えたいなら，自分でコマンドに `*OPC?` を付加しても全く構いません．
```python
device.command('OUTP ON; *OPC?').set()
```

イーサーネットではなく，USB や RS-232 などでコントロールするデバイスに対しては，デバイスツリーの対応する部分を置き換えます．
例えば，USB 接続を VISA 経由で使用するデバイスでは，以下のようになります：
```python
from slowpy.control import control_system as ctrl
ctrl.load_control_module('VISA')    # VISA は SlowPy プラグインとして提供されているので load する
device = ctrl.visa(XXXXXX).scpi()

(あとは同じ)
```


#### この先
- `SlowdashProject.yaml` に `task` のエントリを作ると，スクリプトの自動実行を設定できます．
- `SlowdashProject.yaml` に セキュリティ設定をすると，スクリプトをブラウザから編集できるようにできます．
- ブラウザに入力エリアやボタンを配置して，ボタンクリックでスクリプト中の任意の関数を呼び出すようにすることができます．
- スクリプト中でヒストグラムやグラフを作成して，データベースに保存したりブラウザにストリーミングすることができます．

これらの手順については，公式ドキュメントの「プロジェクト設定」や「コントロールスクリプト」の章を参照してください．


# Docker コンテナで使う
### 基本
DockerHub と GitHub に SlowDash のコンテナイメージがあります．どちらも同じです．

- DockerHub: [slowproj/slowdash:TAG](https://hub.docker.com/r/slowproj/slowdash/tags)
- GitHub Container Registry: [ghcr.io/slowproj/slowdash:TAG](https://github.com/slowproj/slowdash/pkgs/container/slowdash)

コンテナ内での SlowDash プロジェクトディレクトリは `/project` です．これをボリュームマウントして使ってください．以下は，`SlowdashProject.yaml` ファイルが作ってあるプロジェクトディレクトリからコンテナの SlowDash サーバーを実行する例です．
```console
$ docker run --rm -p 18881:18881 -v $(pwd):/project slowproj/slowdash
```

毎回打つのは大変なので，`docker-compose.yaml` を使うのが簡単です．SlowDash の `ExampleProjects` 以下にあるプロジェクト例には，すべて `docker-compose.yaml` ファイルが含まれています．
```yaml
services:
  slowdash:
    image: slowproj/slowdash
    volumes:
      - .:/project
    ports:
      - "18881:18881"
```
このファイルがある場所で `docker compose up` とすればイメージがダウンロードされ，実行が開始されます．（初回は少し時間がかかります．）
```console
$ docker compose up
```

SlowDash のコマンドを使用したい場合，`docker run` または `docker compose up` でコンテナを走らせてから，`docker exec` でコンテナの中から実行してください．
```console
$ docker ps
CONTAINER ID   IMAGE         COMMAND                   CREATED          STATUS         PORTS       NAMES
70e0b99483ae   slowdash      "/slowdash/app/docke…"   10 seconds ago   Up 9 seconds   18881/tcp   elastic_jackson
$ docker exec -it 70e    slowdash config -i4       （70e は上の行で表示されているコンテナID； -i4 は整形オプション）
{
    "slowdash": {
        "version": "250128 \"Skykomish\""
...
```

# SlowDash のアップデート
## 直接インストール
Make を使って更新をできます：
```console
$ cd PATH/TO/SLOWDASH
$ make update
```

手動で行う場合は，`git pull` の際に`--recurse-submodule` を忘れないようにしてください．
```console
$ cd PATH/TO/SLOWDASH
$ git pull --recurse-submodules
$ make
```
この `--recurse-submodules` を忘れることがとても多いです．そして，その場合には，異なるバージョンのソースが混ざるので，それに気づかないとデバッグがとても難しくなります．上記の `make update` を使うのがおすすめです．

## Docker コンテナ
latest タグの SlowDash コンテナを使っている場合，`docker pull` コマンドで最新のものに置き換えることができます．
```console
$ docker pull slowproj/slowdash
```
または，compose のディレクトリから compose コマンドで行うこともできます．
```console
$ docker compose pull
```
使用中の SlowDash バージョンが SlowDash のホーム画面の左上に表示されているので，ここでちゃんと更新されたかを確認できます．


# 動作確認用テスト環境
SlowDash が頻繁に利用するデータベースや Jupyter などを集めたコンテナが `slowdash/utils/testbench` にあります．
システム開発時に本番用のデータベースを使いたくない場合や，開発用サーバのインストールが面倒な場合に，すぐに使えてすぐに消せて便利です．
```console
$ cd PATH/TO/SLOWDASH/utils/testbench
$ docker compose up
$ docker compose down   （終了後データを消す）
```
PostgreSQL, MySQL, InfluxDB, Redis, MQTT, Jupyter などがすべて使えるようになります．
（これらがすでに走っている場合は，ポートが衝突してエラーになるので，コメントアウトかポート番号の変更が必要です．）

このテスト環境は，SlowDash 自体がコンテナに入っていなくても（直接実行でも）使えます．
SlowDash をコンテナ内で使用する場合でも，設定ファイルやスクリプトの開発はコンテナの外で（SlowDash だけはターミナルで直接実行）して，ある程度完成してからコンテナに入れた方が，変更のたびにコンテナの再起動をしなくて済むので楽です．

# セキュリティについて
<b>SlowDash は，ファイアウォールの内部で使う目的で作られています．</b> このためセキュリティ関係の機能は実装されていません．SlowDash のポートを外部からアクセスできるところに開けないようにしてください．外部からは，VPN もしくは SSH のトンネルを経由して使用するのが想定です．


### 基本認証

もし内部の人を信用できない場合，最低限として，基本認証を使ってパスワードを設定することはできます．
`SlowdashProject.yaml` に `authentication` エントリを追加し，パスワードハッシュを指定してください．

```yaml
slowdash_project:
  ...

  authentication:
    type: Basic
    key: slow:$2a$12$UWLc20NG5E3drX35cfA/5eFxuDVC0U79dGg4UP/mo55cj222/vuRS
```

パスワードハッシュは，Apache の bcrypt と同じ形式ですが，`slowdash/utils` にある `slowdash-generate-key.py` プログラムで作ることもできます．
```console
$ python3 PATH/TO/SLOWDASH/utils/slowdash-generate-key.py slow dash
{
    "type": "Basic",
    "key": "slow:$2a$12$UWLc20NG5E3drX35cfA/5eFxuDVC0U79dGg4UP/mo55cj222/vuRS"
}
```

ここでのパスワードは，暗号化せずにやりとりされるので，基本認証を使う場合は HTTPS を使って通信を暗号化する必要があります．
これは，外部のリバースプロキシを使って行うことが想定されています．

SlowDash をデフォルトの ASGI モードで使っている場合は，リバースプロキシの代わりに，組み込みの HTTPS サーバーを使うこともできます．SSL/TLS 鍵ファイルと認証ファイルを指定して `slowdash` を起動してください．
```console
$ slowdash  --port=18881  --ssl-keyfile=KEY_FILE  --ssl-certfile=CERT_FILE
...
Listening at port 18881 (ASGI HTTPS)
```
ただし，この機能は将来の SlowDash では削除されるかもしれません．長期使用するシステムでは，ちゃんとしたリバースプロキシを使用するのがいいと思います．

# リバースプロキシ
SlowDash はデフォルトで暗号化されていない HTTP/1.1 を使用します．これに，Nginx や Apache などの外部のリバースプロキシを接続し，HTTP/2 などに乗せ替えることで，通信を暗号化し，また，ブラウザとの間で HTTP/2 の効率的な通信を使用できるようになります．通常，ここが通信上のボトルネックで，これをするとレスポンスがかなり良くなることが多いです．（SlowDash に HTTP/2 を喋らせることもできますが，広く使われているリバースプロキシを使用する方がトラブルに遭遇したときの対処が楽です．）

### Docker Compose
SlowDash を Docker Compose で使う場合，その中に Nginx または Apache を含めてリバースプロキシとする例が `ExampleProjects/ReverseProxy` にあります．多くの場合，証明書類を置き換えるだけでそのまま使えるはずです．

```yaml
services:
  nginx:
    build: ./nginx
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - slowdash

  slowdash:
    image: slowproj/slowdash
    expose:
      - "18881"
    volumes:
      - .:/project
```

ここでは SlowDash のポートは外部に接続されていないことに注意してください．

`ExampleProjects/ReverseProxy/Nginx` の下には，`nginx` という名前で Nginx の設定ファイルがあります（Apache の方もほぼ同様です）．
```console
$ tree Nginx
Nginx/
├── SlowdashProject.yaml
├── docker-compose.yaml
└── nginx
    ├── Dockerfile
    ├── certs
    │   ├── fullchain.pem
    │   └── privkey.pem
    ├── default.conf
    ├── generate-htpasswd.sh
    ├── generate-selfsigned-certificates.sh
    └── htpasswd
```
使用する前に，`nginx` サブディレクトリもコピーし，さらに，その下の `certs` に証明書類を，`htpassword` ファイルにパスワードを設定しておいてください．
`htpassword` の中身は，基本認証の `"key"` の値の一行です（上記の例で `slow:` から始まる部分）．
内部使用のためのオレオレ証明書を，`generate-selfsigned-certificates.sh` により作成できます．
(ホスト名が外部から解決できる場合は Let's Encrypt でちゃんとした証明書を無料で取得できます．その瞬間だけ外部からアクセスできるようにして，SlowDash を走らせる前に閉めるという方法もあるようです．）

準備ができたら，`docker compose up --build` して，ブラウザから `https://localhost/slowdash/` にアクセスしてください．（`--build` オプションは，パスワードや設定ファイルを変更した場合だけ必要です．）

### 直接インストール
SlowDash にコンテナを使っていない場合でも，リバースプロキシだけを Docker で動かすこともできます．この場合の設定は，すべてを Docker Compose で使う場合とほぼ同じになります (`docker-compose.yaml` の slowdash を削除し，`nginx/defaults.conf` の `proxy_pass` をホストマシンにする)．SlowDash のポートが外部から直接アクセスできないようにファイアーウォールを設定してください．

すべてを Docker でない環境で使う場合の設定方法は，使用している環境に合わせた方法を AI が詳しく教えてくれます．SlowDash では ASGI インターフェースが利用可能で，同じポート番号で WebSockets も使っている旨を伝えれば，設定ファイルを一通り書いてくれます．暗号化していないもとのポートを塞いでおくのを忘れないでください．参考までに，上記の例で Nginx を Docker Compose 内でリバースプロキシとして使用する場合の設定ファイルを示します．だいたい似たような感じになると思います．

```conf
server {
    listen 443 ssl;
    http2 on;
    server_name localhost;   # これは自分のホスト名に変える

    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
    ssl_prefer_server_ciphers off;

    auth_basic "SlowDash Password Required";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location /slowdash/ {
        proxy_pass http://slowdash:18881/;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SlowDash では Long Polling を使っているので，タイムアウトは長くする
        proxy_read_timeout 8640000s;  # 1000 days for long polling used in SlowDash
        proxy_send_timeout 8640000s;  # 1000 days for long polling used in SlowDash
        proxy_connect_timeout 10s;
    }
}

# HTTP への接続は HTTPS に転送する
server {
    listen 80;
    server_name localhost;
    return 301 https://$host$request_uri;
}
```


<div style="margin-bottom:10rem"/>
