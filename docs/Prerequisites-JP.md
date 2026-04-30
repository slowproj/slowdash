---
title: 事前知識
---

# はじめる前に
このページは、SlowDash のドキュメント（特に [Installation](Installation.html)、[Quick Tour](QuickTour.html)、[Project Setup](ProjectSetup.html)、[Data Binding](DataBinding.html)）を読む前に必要な最小限の知識をまとめたものです．この文書は Claude によって自動で作成されました．

SlowDash のドキュメントでは，読み手は次のことができることを前提にしています．

- ターミナルでコマンドを実行できる
- テキストファイル（YAML, Python, HTML）を編集できる
- Python スクリプトの実行ができる
- データベースのテーブルの基本概念を理解している

不安がある場合でも、以下の要点だけ押さえれば開始できます．

# ターミナルの基本
以下のコマンド操作に慣れているとスムーズです．

```console
$ pwd                 # 現在のディレクトリを表示
$ ls -la              # ファイル一覧を表示
$ cd PATH/TO/DIR      # ディレクトリを移動
$ mkdir MyProject     # ディレクトリを作成
$ python script.py    # Python スクリプトを実行
```

SlowDash のチュートリアルでは，ターミナルを2つ使います．

- 1つ目：SlowDash 本体を起動
- 2つ目：テストデータ生成やユーザースクリプトを実行

# Python と仮想環境
ネイティブ環境では、SlowDash は `make` の中で準備されるプロジェクト内 `venv` を使う構成です．

代表的な流れ：

```console
$ source PATH/TO/SLOWDASH/bin/slowdash-bashrc
$ slowdash-activate-venv
$ python your-script.py
```

`venv` の役割：

- 依存関係を分離できる
- システムの Python を汚しにくい
- スクリプトから `slowpy` を利用しやすい

SlowDash 利用者として押さえるポイント：

- `venv` が隔離された Python 実行環境であることを理解する
- 新しいターミナルを開いたら `slowdash-activate-venv` を実行する

有効化後の確認に便利なコマンド：

```console
$ echo "$VIRTUAL_ENV"
$ which python
$ which pip
```

`$VIRTUAL_ENV` にパス（例：`.../venv`）が入っていて，`python` と `pip` がその環境を指していれば有効化できています．

`venv` 有効化中のポイント：

- シェルプロンプトに `(.venv)` が表示されることが多い（シェル設定によります）
- `python` と `pip` は `.venv/bin/...` を指す
- `pip install` したパッケージはその環境内に閉じる

## システム Python が古すぎる場合
OS に標準で入っている Python が EOL（End-of-Life）に達している場合は、そのまま使わないことを推奨します．
`pyenv` でサポート中の Python を先に選び、その後に通常どおり `make` を実行して SlowDash に `venv` を準備させる運用が安全です．

例：

```console
$ pyenv install 3.12.9
$ pyenv local 3.12.9
$ make
$ source PATH/TO/SLOWDASH/bin/slowdash-bashrc
$ slowdash-activate-venv
```

新しいターミナルで `pyenv` を自動有効化する設定 (`.bashrc`)：

```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
```

`.bashrc` を編集したら、現在のシェルで再読み込みします：

```console
$ source ~/.bashrc
```

確認コマンド：

```console
$ pyenv version
```

使い分けの考え方：

- `pyenv`：Python 本体のバージョン管理
- `venv`：プロジェクト依存パッケージの隔離
- 併用すると、再現性とセキュリティ更新の両方を確保しやすい

# YAML
プロジェクト設定は YAML で記述します．

最小例：

```yaml
slowdash_project:
  name: QuickTour
  title: SlowDash Quick Tour
  data_source:
    url: sqlite:///QuickTourTestData.db
    time_series:
      schema: testdata[channel]@timestamp(unix)=value
```

YAML の重要ポイント：

- インデントに意味がある（タブではなくスペースを使用）
- `key: value` で項目を定義
- 深いインデントで入れ子を表現

# データの時刻の表現形式
データを記録するときは、各データに時刻情報が付きます．
この節では、その時刻情報そのものの表現形式を説明します．

- `unix`：`1970-01-01 00:00:00 UTC`（UNIX epoch）からの経過秒で，タイムゾーンに依存しない
- `with time zone`（または `aware`）
- `without time zone` / `naive`（通常は非推奨）
- `unspecified utc`（タイムゾーン文字列なしだが UTC と分かっている）

実務上の違い：

- `unix` は「経過時間」を表す数値表現
- それ以外は、年月日時分秒で記述する日時文字列表現

迷ったら、まず `unix` を使うのが安全です．

# RDBMS と SQL の基礎
SlowDash では、PostgreSQL、MySQL、SQLite などの SQL データベース（RDBMS）をデータソースとして使うことが多いです．
最初のイメージとしては、RDBMS は Excel のような表形式データを複数のテーブルに格納する仕組みだと考えると分かりやすいです．
（厳密には、RDBMS にはテーブル間のリレーションを定義する仕組みがありますが、この導入ではまず表形式データのイメージを優先します．）

最小限の概念:

- **table**: 行と列で構成されるデータの集合
- **row**: 1件のレコード（例: 1時刻の測定値）
- **column**: 属性（`timestamp`, `channel`, `value` など）
- `PRIMARY KEY`: 行を一意に識別するキー（時系列では timestamp + channel の組がよく使われます）

最低限読めるとよい SQL:

- `SELECT ... FROM table`：データの読み出し
- `WHERE ...`：行の絞り込み
- `ORDER BY ...`：並び替え
- `LIMIT N`：取得件数の上限指定

例:

```sql
SELECT timestamp, channel, value
FROM testdata
WHERE channel = 'ch00'
ORDER BY timestamp DESC
LIMIT 10;
```

Quick Tour を進めるだけなら高度な SQL は不要ですが、この基礎があると Data Binding の確認やトラブルシュートがしやすくなります．

# データ記録テーブルの構造記述
次に必要なのは、データ記録テーブルの構造をどう表すかです．
つまり「どの列が時刻で、どの列がチャンネルで、どの列が値か」を記述します．
SlowDash ではこの構造記述を「スキーマ記述子」と呼びます．

よく使う形：

```
table[tag]@time_column(type)=value_column
```

例：

- `testdata[channel]@timestamp(unix)=value`
- `numeric_data[endpoint]@timestamp(with timezone)=value_raw`

意味：

- `table`：読み出し元テーブル（または measurement）
- `[tag]`：チャンネル名として使う列
- `@time_column(type)`：時刻列とその型
- `=value_column`：値の列

# ネットワークとポートの基本
SlowDash の例ではポート `18881` をよく使います．

- ブラウザで `http://localhost:18881` を開く
- Docker 利用時は `-p 18881:18881` を設定
- そのポートが他プロセスで使用中でないことを確認

# Docker / Docker Compose の基礎
SlowDash において、コンテナは必須ではなくオプションです．
コンテナに慣れていない場合は、最初から Docker を使う必要はありません．まずはネイティブ構成で始めて問題ありません．

最初にコンテナを使わなくてよいケース：

- SlowDash の基本操作を学ぶ段階
- 単一マシンでシンプルに運用する段階
- トラブルシュート時に構成要素を減らしたい場合

コンテナに慣れていない場合は、まず次のイメージを持つと分かりやすいです．

- **コンテナイメージ**：コマンドとその実行環境（依存ライブラリや設定）をまとめた実行用パッケージ
- **コンテナ**：イメージから起動される実行中のインスタンス
- Docker：1つのコンテナをコマンドで起動・停止する仕組み
- Docker Compose：複数の関連コンテナをまとめて管理する仕組み

SlowDash での意味合いは次の通りです．

- Docker さえ使える環境なら、既存の SlowDash コンテナイメージを取得して、ホスト側に SlowDash 本体をインストールせずに使い始められる
- ホスト環境に SlowDash の Python 依存を直接入れなくてもよい
- プロジェクトファイルはホスト側に置いたまま使える
- SlowDash プロセス本体はコンテナ内で動作し、マウントされたプロジェクトを読み書きする

コンテナ導入で得られる主なメリット：

- 再現性：実行環境をマシン間で揃えやすい
- ホスト環境の清潔性：グローバルな Python パッケージ汚染を減らせる
- チーム共有のしやすさ：同じイメージと compose 設定で実行できる
- 更新・ロールバックの容易さ：イメージタグ切り替えで管理しやすい
- 複数サービス連携：DB／リバースプロキシ／ノートブック等との併用がしやすい

例でよく出るオプションの意味：

- `-v $(pwd):/project`
  - 左側 `$(pwd)`：ホスト側の現在ディレクトリ
  - 右側 `/project`：コンテナ内のパス
  - 効果：ホストで編集したファイルがコンテナからすぐ見える
- `-p 18881:18881`
  - 左側：ホスト側ポート
  - 右側：コンテナ側ポート
  - 効果：`http://localhost:18881` へのアクセスがコンテナ内 SlowDash に届く
- `--rm`
  - 停止後にコンテナを自動削除する
  - 試行用の一時実行に向いている

最小の単体コンテナ例:

```console
$ cd YOUR_PROJECT_DIR
$ docker run --rm -p 18881:18881 -v $(pwd):/project slowproj/slowdash
```

このコマンドで起きること：

1. 必要なら Docker がイメージを取得する
2. コンテナが起動し、内部で SlowDash が動く
3. ブラウザで `http://localhost:18881` を開いて利用する
4. 停止するとコンテナは削除される（`--rm`）が、ホスト側のプロジェクトファイルは残る

最小の Docker Compose 例:

実運用では、データベースもホストに直接インストールせず、コンテナで使いたい場合がよくあります．
この場合、SlowDash コンテナとデータベースコンテナを同時に動かす必要があり、少なくとも2つのコンテナを管理することになります．
Docker Compose は、この複数コンテナの起動・停止を1つの設定ファイルから自動化する仕組みです．

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      - POSTGRES_USER=slowdash
      - POSTGRES_PASSWORD=slowdash
      - POSTGRES_DB=slowdash
    volumes:
      - postgres-data:/var/lib/postgresql/data

  slowdash:
    image: slowproj/slowdash
    depends_on:
      - postgres
    volumes:
      - .:/project
    ports:
      - "18881:18881"

volumes:
  postgres-data:
```

Docker Compose を使う利点：

- 複数コンテナを手で順番に起動する作業が不要になる
- `docker compose up` 1回で SlowDash + DB を同時起動できる
- `docker compose down` 1回で同時停止できる
- サービス定義がファイルに残るため、チーム内で共有しやすい

起動と停止：

```console
$ docker compose up
$ docker compose down
```
