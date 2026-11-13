# `kl_pg_store`

[English](README.md)

`kl_pg_store` は, 長期間の実験の時系列データを想定して, `data.store.>` の `DataPacket` を, PostgreSQLに保存するslowtaskです.
PostgreSQLの基本機能を活用し, コア機能はextensionや, 外部ツールに依存しません.
コア概念は他のRDBでの設計にも流用可能です.
KamLAND2実験のslow controlデータの収集のために構築されましたが, **KamLAND実験特有のものはない, 汎用の構成です**.

想定している規模は, channel数 1000, 100 行/秒 (1 message あたり 10 channel), 保存期間は永久 (実験期間 ~30 年) です.
この規模で, 年間 約 32 億行, 約 300 GB になります.

ここには, PostgreSQLのschema定義 (table, view, function, role) と, そのdatabaseに値を保存するslowtask, Slowdash向けの設定の例が含まれています.
他にも管理スクリプトや, dockerで立ち上げる例などもあります.
DBのschema定義は, slowtaskから独立して動きます.
slowtaskを使わずに, 他のアプリケーションから直接 `insert_records()` などのSQL関数を呼んで書き込むこともできます.

## 目次

 - [設計方針](#設計方針)
 - [Dash start](#dash-start)
    - [1. DBを起動する](#1-dbを起動する)
    - [2. Slowdashの設定](#2-slowdashの設定)
    - [3. データを送る, 見る](#3-データを送る-見る)
    - [4. channelの情報を書く](#4-channelの情報を書く)
 - [Core concept](#core-concept)
 - [PostgreSQL databaseの詳細仕様](#postgresql-databaseの詳細仕様)
    - [Install](#install)
    - [dockerのデータ](#dockerのデータ)
    - [INSERT用の関数](#insert用の関数)
    - [値の型](#値の型)
    - [拒否と `rejections`](#拒否と-rejections)
    - [過去データの一括投入](#過去データの一括投入)
    - [channelの管理](#channelの管理)
    - [Partition](#partition)
    - [最新値](#最新値)
    - [Role](#role)
    - [設定](#設定)
    - [直接操作する場合](#直接操作する場合)
    - [Performance, index](#performance-index)
 - [Slowdashからの利用](#slowdashからの利用)
    - [配置](#配置)
    - [Slowdashをdockerで動かす](#slowdashをdockerで動かす)
    - [channelのページ](#channelのページ)
    - [slowtaskの動作](#slowtaskの動作)
 - [採用しなかったこと](#採用しなかったこと)


## 設計方針

 - 入り口は一つ. 書き込みは全て `insert_records()` を通ります. tableへの直接のINSERTは許可しません. 入力の検査, channelの自動作成, partitionの作成, 最新値の更新は全てこの関数の中で行われます.
 - 単純なSQLで取り出せる. データは `records` などのviewに対する普通の `SELECT` や `COPY` で取り出せます. 内部に複雑な仕組みを持ち込まず, Slowdashからも自然なData sourceに見えます.
 - 受け取ったデータは消さない. 拒否した入力も `rejections` tableに全て保存します.
 - Slowdashのmeshとの連携が検証されています.


## Dash start

DBの起動 -> Slowdashの設定 -> データを送る/見る -> channel情報を書く

### 1. DBを起動する
```bash
cd toolbox/tasks/kl_pg_store/docker
echo 'POSTGRES_PASSWORD=<your_password>' > .env     # superuser postgres のpassword
docker compose up -d
docker compose exec db psql -U postgres -d kldb -c '\password kl_writer'
docker compose exec db psql -U postgres -d kldb -c '\password kl_monitor'
```
PostgreSQL 16が起動し, 初回の起動時に `sql/install.sql` でstoreがinstallされます.
roleのpasswordは, 自分で決めて `\password` で設定します (dockerを使わない[Install](#install)と同じです).

環境変数 (`docker/.env` に書きます) は以下です. `KL_DB_PORT` と `KL_DATA` 以外は, 初回の起動時 (databaseの作成時) だけ使われます.

| 変数                | default   | 内容                                                  |
| ------------------- | --------- | ----------------------------------------------------- |
| `POSTGRES_PASSWORD` | (必須)    | superuser `postgres` のpassword                       |
| `KL_DB_PORT`        | `15432`   | 公開するport. 他のhostからも接続できます              |
| `KL_DB_NAME`        | `kldb`    | database名                                            |
| `KL_DATA`           | `kl_data` | データの置き場所. dockerのvolume名か, hostのdirectory |

初期設定は以下です.

 - 接続先は `<DBのhost>:15432` (同じhostからは `localhost:15432`), database `kldb`, schema `kl_store` です.
   portは全てのnetwork interfaceに公開されるので, 閉じたnetworkの中で使ってください.
 - role `kl_admin`, `kl_writer`, `kl_monitor`, `kl_analyzer` が作られます (後述の[Role](#role)).
   passwordを設定していないroleは, containerの外からは接続できず, containerの中からだけ使えます (`docker compose exec db psql -U kl_admin -d kldb`). passwordは, 使うroleにだけ設定します.
 - データはdockerのvolume `kl_data` に保存されます. `docker compose down` では残り, `docker compose down -v` で消えます. 実際の運用では, `KL_DATA=/data/kldb` のようにhostのdirectoryを指定してください (後述の[dockerのデータ](#dockerのデータ)).
 - passwordを後から変える時も, `\password` を使います.
 - `max_locks_per_transaction` は 512 です (`docker-compose.yaml` の `command`. 後述の[ロック表](#ロック表)).

dockerを使わずに, 既存のPostgreSQLにinstallする方法は後述の[Install](#install)にあります.


### 2. Slowdashの設定
`SlowdashProject_example.yaml` の内容を, 自分のprojectの `SlowdashProject.yaml` にコピーします.
```yaml
slowdash_project:
  # name, title, etc. of your project

  # KL_WRITER_DB, KL_MONITOR_DB: PostgreSQL URLs, given as environment variables
  data_source:
    url: ${KL_MONITOR_DB}
    time_series:
      schema: records[name]@ts(with timezone)=value
      tags:
        sql: SELECT DISTINCT name FROM channels WHERE type IN ('double', 'integer', 'boolean')
    object_time_series:
      schema: records[name]@ts(with timezone)=value_jsonb
      tags:
        sql: SELECT DISTINCT name FROM channels WHERE type = 'json'

  task:
    - name: "@toolbox/kl_pg_store"
      auto_start: true
      parameters:
        dsn: ${KL_WRITER_DB}
        spool: ./kl_pg_store-spool.jsonl
```

 - `name`, `title` などは自分のprojectのものです.
 - DBの接続先 (PostgreSQLのURL) は, 環境変数 `KL_WRITER_DB`, `KL_MONITOR_DB` で与えます. 1.のDBなら以下です. 設定していないと, Slowdashのlogに `variable substitution error: KL_WRITER_DB` と出ます.
   ```bash
   export KL_WRITER_DB=postgresql://kl_writer:PASSWORD@localhost:15432/kldb
   export KL_MONITOR_DB=postgresql://kl_monitor:PASSWORD@localhost:15432/kldb
   ```
 - `data_source`: Slowdashのplotは, `kl_monitor` で `records` viewを読みます. 数値は `value` を, histogramなどのobjectは `value_jsonb` を読みます.
 - `task`: slowtask `kl_pg_store` が, `data.store.>` のmessageを受け取って, `kl_writer` でDBに書き込みます. DBに書き込めなかったmessageは `spool` のファイルに残ります (後述の[slowtaskの動作](#slowtaskの動作)).

Slowdashはいつも通りに起動します. Slowdashをdockerで動かす場合は, 後述の[Slowdashをdockerで動かす](#slowdashをdockerで動かす)の手順で, DBに接続します.

### 3. データを送る, 見る
SlowdashのWebMeshに, `data.store.` で始まるtopicで `DataPacket` を送ります. `t` は時刻, `x` は値です.
```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{ "env.laboratory.temperature": { "t": "2026-11-10T21:45:00+09:00", "x": 24.1 } }' \
  http://localhost:18881/api/webmesh/publish/data.store._
```
もう1つ, 10秒後の値を送ります.
```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{ "env.laboratory.temperature": { "t": "2026-11-10T21:45:10+09:00", "x": 24.3 } }' \
  http://localhost:18881/api/webmesh/publish/data.store._
```
`t` は今の時刻にしてください (plotの表示範囲に入るように). `t` は日付, 時刻, timezoneを全て含むISO 8601の文字列か, UNIX time (`date +%s`) です (後述の[INSERT用の関数](#insert用の関数)の `ts`). 1回のPOSTで複数のchannelを送ることもできます.

channel `env.laboratory.temperature` は, 最初の値から型 (`double`) を推定して, 自動的に作られます.

Slowdashの画面で, Channel Listの `env.laboratory.temperature` をクリックすると, plotが表示されます.

SQLで直接読むこともできます (`docker/` で実行します).
```bash
docker compose exec db psql -U kl_monitor -d kldb
```
```sql
SELECT * FROM latest;
SELECT * FROM records
  WHERE name = 'env.laboratory.temperature' AND ts > now() - interval '1 hour'
  ORDER BY ts DESC LIMIT 10;
```

### 4. channelの情報を書く
自動で作られたchannelには, unitとdescriptionがありません. 人間が書き足します.
```sql
SELECT describe_channel('env.laboratory.temperature', 'degC', 'Laboratory room temperature');
SELECT name, type, unit, description FROM channels;
```
`kl_monitor` の権限でも実行できます.

channelは, データを送る前に作っておくこともできます.
```sql
SELECT create_channel('env.laboratory.pressure', 'double', 'hPa', 'Laboratory room pressure');
```
こちらは `kl_writer` (または `kl_admin`) で実行します (`docker compose exec db psql -U kl_writer -d kldb`).

多くのchannelをまとめて書く時は, 管理スクリプト `utils/kl_admin.py` でCSVから書けます (後述の[管理スクリプト](#管理スクリプト)).

Slowdashの画面からも書けます. slowtask `kl_pg_store` は, channelの一覧と, unit, descriptionの入力欄, channelの作成欄を持つHTML panel `kl_channels` を提供します (後述の[channelのページ](#channelのページ)).

とりあえずこれで運用を始められます.


## Core concept

全てのobjectは専用のschema (default: `kl_store`) に置かれます.

`channels` tableは, channel (値として入る変数名) を定義します.
```
| cid | name                         | valid_from | type   | unit | description                 |
| --- | ---------------------------- | ---------- | ------ | ---- | --------------------------- |
| 1   | env.laboratory.temperature   | -infinity  | double | degC | Laboratory room temperature |
| 2   | calc.server01.cpu_usage      | -infinity  | double | %    | server01 cpu usage          |
| 3   | analysis.onlinetool.darkrate | -infinity  | double | cps  | Online average dark rate    |
| .   | ............................ | .......... | ...... | ...  | ........................... |
```
未知のchannelが来ると, 最初の値から型を推定して, 自動的に作成します.
単位や説明は人間が書き足します.
なお, channelのnameは自由な形式で名付けることができますが, ここでは, `<subsystem>.<source>.<quantity>` のruleで命名しています. `source` は値の出どころ (機器名, 機器のchannel, 場所など), `quantity` は物理量です. 一般的に, 実験で一貫したnaming ruleを持つことをおすすめします.

`raw_records` tableは, データをlong format (1行に1つの値) で持つ実体のtableです.
```
| cid | ts                   | inserted_at          | value |
| --- | -------------------- | -------------------- | ----- |
| ... | .................... | .................... | ....  |
| 1   | 2026-10-10T01:10:01Z | 2026-10-10T01:10:01Z | 23.5  |
| 1   | 2026-10-10T01:10:02Z | 2026-10-10T01:10:02Z | 23.4  |
| 2   | 2026-10-10T01:10:03Z | 2026-10-10T01:10:03Z | 60.7  |
| 1   | 2026-10-10T01:10:03Z | 2026-10-10T01:10:03Z | 23.5  |
| 3   | 2026-10-10T01:10:04Z | 2026-10-10T01:10:05Z | 13943 |
| ... | .................... | .................... | ....  |
```
実際には, 値の列は型ごとに `value` (double), `value_int`, `value_text`, `value_bool`, `value_jsonb` の5本あり, 各行ではchannelの型に対応する1本だけが値を持ちます.

このtableはとても大きくなるので, 週ごとのpartitionに分けています.

ユーザーは, この実体や, cidの対応付けを意識せずに, `records` viewをnameで読みます.
```sql
SELECT * FROM records
  WHERE name = 'calc.server01.cpu_usage' AND ts > now() - interval '1 day'
  ORDER BY ts DESC LIMIT 10;
```
`records` の列は `name`, `ts`, `value`, `unit`, `type`, `value_int`, `value_text`, `value_bool`, `value_jsonb`, `cid`, `inserted_at` です.
`value` は数値の型 (double, integer, boolean) の値をdoubleにしたもので, textとjsonの値は `value_text`, `value_jsonb` に入ります.
Slowdashも, 数値は `value` を, histogramなどのobjectは `value_jsonb` を, この `records` から読みます.

`records` を読む時は, 必ず `ts` の範囲を指定してください.
運が悪く, 未来のtime partitionが大量に作成されていたり, そのchannelの更新がはるか過去に止まっていたりすると, そのchannelの全期間を読みます.
範囲が分からない時は, `latest` からcidを決めます (後述の[viewを読む時の注意](#viewを読む時の注意)).

書き込みは, 全て `insert_records()` 関数を通ります (後述の[INSERT用の関数](#insert用の関数)).

tableとviewの一覧です.

| 名前                | 種類  | 内容                                                    |
| ------------------- | ----- | ------------------------------------------------------- |
| `channels`          | table | channel定義                                             |
| `records`           | view  | 全てのデータ. nameで引く. Slowdashもここから読む        |
| `latest`            | view  | nameごとの最新値. `records` と同じ列                    |
| `rejections`        | table | 拒否した入力. 削除しない                                |
| `raw_records`       | table | データの実体. cidで引く. 週次partition                  |
| `raw_latest`        | table | cidごとの最新値. `raw_records` から作り直せる派生データ |
| `settings_overview` | view  | 全ての設定の一覧 (読むだけ)                             |
| `settings`          | table | schemaのversion, 受け付ける時間範囲などの設定 (1行)     |
| `channel_log`       | table | channel定義の変更履歴. 削除しない                       |

`raw_` が付くものはcidで引く実体のtableで, 普段は直接読みません.


## PostgreSQL databaseの詳細仕様

### Install
dockerを使わずに, 既存のPostgreSQL (16以降) にinstallする場合は, superuserで以下を実行します.
ubuntuなら, `sudo apt install postgresql libpq-dev` して, `sudo -u postgres psql ...` と実行します.
database `kldb` は先に作っておきます (`createdb kldb`). database名は自由です (この文書の例では `kldb`).
```bash
psql -d kldb -f sql/install.sql
psql -d kldb -c '\password kl_admin'
psql -d kldb -c '\password kl_writer'
psql -d kldb -c '\password kl_monitor'
psql -d kldb -c '\password kl_analyzer'
```
passwordは, 使うroleにだけ設定します.
接続したdatabaseにinstallされます.
`install.sql` は冪等です.
`postgresql.conf` の `max_locks_per_transaction` は大きめ (例えば 512) にしてください (後述の[ロック表](#ロック表)).
変更にはserverの再起動が必要です.
`postgresql.conf` の場所は, installの方法によって違います. `psql -c 'SHOW config_file'` で分かります.
dockerのDBでは `postgresql.conf` を編集せず, `docker-compose.yaml` の `command` に `-c max_locks_per_transaction=512` のように渡しています.

`-v` で指定できる変数は以下で, 全て省略可能です (例: `psql -d kldb -v schema=kl_store -v role_prefix=kl -f sql/install.sql`).

| 変数                       | default    | 内容                                                     |
| -------------------------- | ---------- | -------------------------------------------------------- |
| `schema`                   | `kl_store` | 全てのobjectを置くschema. 作業用schemaは `<schema>_work` |
| `role_prefix`              | `kl`       | roleの名前は `<role_prefix>_admin` など                  |
| `monitor_timeout`          | `30s`      | monitor roleの `statement_timeout`. roleの作成時だけ設定 |
| `monitor_connection_limit` | `20`       | monitor roleの接続数の上限. roleの作成時だけ設定         |

Slowdashからは, 接続先を環境変数 `KL_WRITER_DB`, `KL_MONITOR_DB` (PostgreSQLのURL) で指定します.

### dockerのデータ
dockerのDBのデータ (PostgreSQLのdata directory) の置き場所は, `KL_DATA` で選びます.

| `KL_DATA`                    | 置き場所                     | 消える操作                                      |
| ---------------------------- | ---------------------------- | ----------------------------------------------- |
| `kl_data` (default)          | dockerが管理するvolume       | `docker compose down -v`, `docker volume prune` |
| `/data/kldb` など (絶対path) | hostのdirectory (bind mount) | directoryを消した時だけ                         |

試す時はdefaultで構いません. 実際の運用では, hostのdirectoryを指定します. 置き場所が分かるので, diskの選択 (容量は年 約300 GB), backup, 移行がしやすく, dockerの操作で誤って消えることもありません.
directoryは空の状態で指定します. 初回の起動時に, そこにdatabaseが作られます.

### INSERT用の関数
partitionの作成や, 矛盾のないデータの整理ができるのは, tableへの直接のINSERTを許さず, 入力を `insert_records()` だけに集中させているからです.
この関数が, 入力データとchannel定義の整合性を保ちます.
slowtaskは内部でこの関数を呼んでいます.
slowtask (やSlowdash) を使わずに, DBの定義だけを使う場合も, 入力の検査はSQLの関数が責任を持ちます.

```sql
SELECT * FROM insert_records('[
  { "name": "env.laboratory.temperature", "ts": "2026-10-10T01:10:01Z", "value": 23.5 },
  { "name": "env.laboratory.humidity",    "ts": 1791594601.25,          "value": 48.1 }
]');
```

`insert_records(records jsonb, update_latest boolean DEFAULT true)` の `records` は, `name`, `ts`, `value` を持つobjectのJSON配列です.
実行できるroleは admin と writer です.

 - `ts` は日付, 時刻, timezoneを全て含むISO 8601の文字列 (`2026-10-10T01:10:01Z`, `2026-10-10 10:10:01.5+09:00` など) か, UNIX time (秒, 小数可) です.
   日付だけ (`2026-10-10`) やtimezoneの無い文字列は, 補わずに拒否します. 補うと, timezoneの解釈が設定によって変わったり, 同じ日の値が全て `duplicate` になったりするためです. 秒は省略できます.
   ミリ秒のUNIX time (`1791594601250` など) は `invalid_record` として拒否します.
 - `ts` を省略した場合 (または `null` の場合) は, serverの時刻 (`statement_timestamp()`) を使います. この時 `inserted_at` と同じ値になるので, `ts = inserted_at` の行は, serverで時刻を補ったものと判断できます.
 - 戻り値は, 書き込めなかったrecordだけの一覧 (`input_index`, `status`, `cid`, `detail`) です. 空なら全て書き込めています.
 - `update_latest => false` にすると, 最新値の表 (`raw_latest`) を更新しません. CSVからの過去データの一括投入など, 最新値が変わらないと分かっている場合に使います.

1回の呼び出しは1つのtransactionです.
recordごとに検査して, 通らなかったrecordを `rejections` に回します.
性能のために, recordごとの例外処理 (subtransaction) は使いません.
想定外のエラー (DBの障害など) が起きた場合は, 呼び出し全体が失敗します.

#### その他の書き込み関数

| 関数                                                               | 用途                                                  | 実行できるrole |
| ------------------------------------------------------------------ | ----------------------------------------------------- | -------------- |
| `insert_record(name text, ts timestamptz, value double precision)` | 1つの数値を書き込む. `insert_records()` の薄いwrapper | admin, writer  |
| `insert_record_by_cid(cid integer, ts timestamptz, value jsonb)`   | low-levelな管理用. cidを直接指定する                  | admin          |

`insert_record_by_cid()` は, 管理者が過去のデータを補完するためなどに使います.
型の推定やchannelの自動作成は行わず, 受け付ける時間範囲の検査もしません.
ただし, そのcidの有効期間 (後述の `valid_from`) の外の `ts` は拒否します.
`ts` は省略できません.

### 値の型
channelの型は `double`, `integer`, `boolean`, `text`, `json` の5種類です.
channelの型は作成時に決まり, 以後変わりません. 型を変える時は, 新しいcidのchannelに入れ替えます (後述の `replace_channel()`).

未知のchannelに最初の値が来ると, その値から型を推定してchannelを自動作成します.
channelが作られるのは, 最初の値が書き込める場合だけです. 拒否された値でchannelが作られることはありません.

| 最初の値 (JSON)                                       | 推定する型                         |
| ----------------------------------------------------- | ---------------------------------- |
| number (整数も含む), `true` / `false`                 | `double`                           |
| string                                                | `text`                             |
| object / array (histogramなど)                        | `json`                             |
| `null`, 文字列の `"NaN"`, `"Infinity"`, `"-Infinity"` | 推定しない (channelを作らずに拒否) |

`integer` と `boolean` は推定では作られません. 必要な場合は `create_channel()` で事前に作成してください.
`double` 型では絶対値が `2**53` を超えない整数は正確に表現できるので, 多くの場合 `double` で十分です.

作成済みのchannelには, 情報が失われない範囲で変換して書き込みます.

| 来た値 \ channelの型 | double    | integer              | boolean      | text                 | json |
| -------------------- | --------- | -------------------- | ------------ | -------------------- | ---- |
| number               | ✓         | 整数かつ範囲内なら ✓ | 0 / 1 なら ✓ | ✓ (文字列にする)     | ✓    |
| `true` / `false`     | ✓ (1 / 0) | ✓ (1 / 0)            | ✓            | ✓                    | ✓    |
| string               | ✗         | ✗                    | ✗            | ✓                    | ✓    |
| object / array       | ✗         | ✗                    | ✗            | ✓ (JSON文字列にする) | ✓    |
| `null`               | ✗         | ✗                    | ✗            | ✗                    | ✗    |

`double` では, NaN と ±Infinity は拒否します.
`double` に `2**53` を超える整数が来た場合は, 最も近いdoubleに丸めて書き込みます. JSONの数値はdoubleとして送られることが多く, 整数の形の文字列から元が整数だったかどうかは区別できないためです. 正確な整数が必要なchannelは `integer` で作ってください.
JSONではNaNを表現できないので, slowtaskは非有限の値を文字列 `"NaN"` などとして送ります.

推定が外れた場合は, 後述の `replace_channel()` で型を切り替えます.

### 拒否と `rejections`
以下の入力は拒否し, 元の入力のまま `rejections` tableに保存します.
`rejections` は誰かが日常的に読むものではありませんが, 受け取ったデータは消さないという原則のために存在します.

| `status`                 | 内容                                                                                      |
| ------------------------ | ----------------------------------------------------------------------------------------- |
| `invalid_record`         | 形式の不正 (objectでない, nameが空, `ts` が解釈できない, など)                            |
| `invalid_value`          | `null`, NaN, ±Infinity                                                                    |
| `type_mismatch`          | 上の表の ✗                                                                                |
| `timestamp_out_of_range` | 受け付ける時間範囲の外                                                                    |
| `out_of_validity`        | `ts` がそのnameの最初の `valid_from` より前. cid指定の書き込みでは, そのcidの有効期間の外 |
| `duplicate`              | 同じchannel, 同じ `ts` の値が既にある                                                     |
| `dropped`                | 入力の拒否ではなく, `drop_channel()` で削除したchannelのデータ                            |

同じchannelで同じ `ts` の値は, 先に来た値を残し, 後から来た値を `duplicate` として拒否します.
同じデータを再送しても, 二重に保存されることはありません.
`merge_channel()` でデータを移した時に, 移し先に同じ `ts` の値があった場合も, 移し先の値を残し, 移す方の値を `duplicate` として `rejections` に移します.

`merge_channel()` と `drop_channel()` が `rejections` に移したデータの `record` は, `insert_records()` の入力の形 (`name`, `ts`, `value`) に, 元の `cid` と `inserted_at` を加えたものです.
`insert_records()` に渡し直せます.

`rejections` は削除しないので, 設定を誤った送信側があると増え続けます. 時々以下のように確認してください.
```sql
SELECT status, record->>'name' AS name, count(*), max(received_at)
FROM rejections WHERE received_at > now() - interval '1 day'
GROUP BY 1, 2 ORDER BY 3 DESC;
```

受け付ける時間範囲は, `settings` tableの `max_past`, `max_future` で指定します.
defaultは過去, 未来とも100年で, 実質的に制限しません.
時計のずれた機器 (時計が1970年に戻った, など) からのデータが, 誰も見ない時期に散らばるのを防ぎたい場合は, 短く設定します (例: `UPDATE settings SET max_past = '2 months', max_future = '1 day';`). 負の値は指定できません.

### 過去データの一括投入
他のsystemからの移行など, 過去のデータを大量に入れる場合も, `insert_records()` で入れます.
1回の呼び出しに1000 record程度をまとめると速くなります.
CSV (列は `name`, `ts`, `value`) を入れるscriptの例です.

```python
import asyncio, csv, json, sys
import asyncpg

async def main(path, dsn):
    conn = await asyncpg.connect(dsn)
    with open(path, newline='') as f:
        rows = list(csv.DictReader(f))
    for i in range(0, len(rows), 1000):
        batch = [{'name': r['name'], 'ts': r['ts'], 'value': float(r['value'])} for r in rows[i:i + 1000]]
        rejected = await conn.fetch('SELECT * FROM insert_records($1::jsonb, update_latest => false)', json.dumps(batch))
        for r in rejected:
            print(i + r['input_index'], r['status'], r['detail'], file=sys.stderr)
    await conn.close()

asyncio.run(main(sys.argv[1], 'postgresql://kl_writer:PASSWORD@localhost:15432/kldb'))
```

 - 速さ: 1接続で 約4万行/秒, 8接続で並列に呼ぶと 約30万行/秒でした (batch 1000. 2年分 60億行の入ったDB, Apple M4 Max). 1 秒周期のchannelの1年分 (3150万行) は, 1接続で 約13分です.
 - 容量: 1行あたり, table と index で 約100 B, WALが 約170 B です. WALをarchiveしている場合や, standbyがある場合は, その分の容量と転送も必要です.
 - 行は `ts` の順に入れてください. 1回の呼び出しが触るpartitionが少なくなり, BRIN indexも効きます.
 - 古い週のpartitionは `insert_records()` が作ります. `max_past` を短くしている場合は, 投入の間だけ戻します.
 - 通常の書き込み (slowtask) と同時に行えます. 試験では, 8接続で上限まで書いている間も, 通常の書き込みの応答時間は変わりませんでした.
   ただし, 投入の最中に `replace_channel()` などを実行すると, 投入の呼び出しが終わるのを待つ間, 全ての書き込みが止まります (後述の[ロック](#ロック)).
 - `update_latest => false` の時は最新値を更新しないので, 新しく作られたchannelは `latest` に出ません. 投入の後に admin で `SELECT rebuild_latest();` を実行します.
 - 投入の後に, 他に長いtransactionが無い状態で, admin でvacuumします.
   ```sql
   VACUUM (ANALYZE) raw_records;
   ```
   vacuumは, 行が全ての接続から見えることを visibility map に記録します.
   記録が無いと, Slowdashのplotのqueryがindexだけで答えられずにheapを読むので, 10倍以上遅くなります (1 秒周期のchannelの30日分で, 0.57秒が5.2秒).
   autovacuumも後で行いますが, その時に長いtransaction (psqlで `BEGIN` したままの接続, `insert_records()` を通さない大きなINSERTなど) があると記録できません.
   `pg_stat_activity` の `xact_start` で確認できます.
   2年分 (554 GB) で 約15分 (`vacuumdb -j 8`) でした.

### channelの管理

#### 期間とcid
channelの一意性は `(name, valid_from)` で, 同じnameを複数のcidが期間を分けて持てます.
各channelの有効期間は `[valid_from, 次のvalid_from)` です.
nameの最初のchannelの `valid_from` は `-infinity` (全期間有効) です.

nameで書き込む時は, `valid_from <= ts` を満たす中で `valid_from` が最も新しいchannelに入ります.
期間を区切るのは `replace_channel()` だけです.

読む時は, viewがcidでjoinしているので, nameで引くと複数のcidの履歴がつながって返ります.
各行の `unit` や `type` は, その行のcidのものです.
channelの期間は重ならないので, 同じnameで同じ `ts` の行が2つ返ることはありません.

#### 関数

| 関数                                                                         | 用途                                        | 実行できるrole         |
| ---------------------------------------------------------------------------- | ------------------------------------------- | ---------------------- |
| `create_channel(name, type, unit, description)`                              | 新しいnameを作る                            | admin, writer          |
| `describe_channel(name or cid, unit, description)`                           | unit, descriptionを書く                     | admin, writer, monitor |
| `replace_channel(name, valid_from, type, unit, description, allow_rounding)` | 時刻 `valid_from` から別のchannelにする     | admin                  |
| `rename_channel(name or cid, new_name)`                                      | nameを付け直す                              | admin                  |
| `merge_channel(cid, into_name, allow_rounding)`                              | cidのデータを別のnameに移し, cidを消す      | admin                  |
| `drop_channel(cid)`                                                          | channelを消す. データは `rejections` に移す | admin                  |

 - `create_channel()`: nameが既にあり, 型が同じなら, 何もせずに今のcidを返します. DAQの起動scriptから毎回呼ぶ使い方を想定しています. 型が違う場合はエラーです. 既存のchannelのunit, descriptionは書き換えません (違う値を渡すとWARNINGを出します).
 - `describe_channel()`: nameで指定すると, `valid_from` が最も新しいcidを書き換えます. `replace_channel(name, 未来のT)` で切り替えを予定している場合は, 切り替え後のchannelです. 過去の期間はcidで指定します. 渡した値がそのまま入ります (unitとdescriptionの両方を渡します). `NULL` は未記入で, 自動作成されたchannelが持ちます. `''` は記入済みで空 (unitなら単位の無い量. `ratio_ab` など) です. `NULL` を渡すと未記入に戻ります. channelのページと管理スクリプトのCSVは `NULL` を渡さず, 空欄は `''` として書きます. unitとdescriptionしか変えないので, monitorにも許可しています. channelのページ (後述の[channelのページ](#channelのページ)) や管理スクリプトから呼ぶことを想定しています.
 - `replace_channel()`: 「このnameは, 時刻 `valid_from` から別のchannel (新しいcid) になる」という操作です. `type`, `unit`, `description` は, 省略すると切り替え前のchannelのものを引き継ぎます. `valid_from` が過去の場合は, 切り替え前のchannelの `ts >= valid_from` のデータを新しいcidに移します. 型が変わる場合は, 全てのデータが情報を失わずに変換できる時 ([値の型](#値の型)の表の ✓) だけ実行し, 1つでも変換できなければエラーにします. `integer` から `double` に変える時に `2**53` を超えてdoubleで正確に表せない値があるとエラーにし, `allow_rounding => true` を付けると丸めて移します.
 - `rename_channel(name, new_name)`: そのnameの全ての期間を改名します. 履歴は全て新しいnameに付いていきます.
 - `rename_channel(cid, new_name)`: 1つの期間だけを, 新しいnameに移します. 新しいnameでは, そのchannelは全期間有効 (`valid_from = -infinity`) になります. 元のnameでは, その期間は1つ前の期間の続きになります (1つ前の期間が無ければ, その期間の `ts` の書き込みは `out_of_validity` で拒否されます).
 - `merge_channel(cid, into_name)`: cidのデータを, `into_name` のchannelへ, それぞれの `ts` で有効なcidに振り分けて移し, cidを消します. `into_name` はcid自身のnameでもよく, `replace_channel()` の取り消しに使います. 型の変換は `replace_channel()` と同じです.
 - `drop_channel(cid)`: channelを消します. データは `dropped` として `rejections` に移すので, 失われません.

`rename_channel()` の `new_name` に既存のnameは指定できません. 既存のnameに合流させる時は `merge_channel()` を使います.

#### ケースごとの操作

| #   | ケース                                                       | 操作                                                              |
| --- | ------------------------------------------------------------ | ----------------------------------------------------------------- |
| 1   | 事前にchannelを決めておく                                    | `create_channel()`                                                |
| 2   | 何もせずデータを送る                                         | 自動作成 (型は最初の値から推定)                                   |
| 3   | DAQの起動scriptが毎回 `create_channel()` を呼ぶ              | 同じ型なら既存のcidを返す. 型が違えばエラー                       |
| 4   | 自動作成の後でunit, descriptionを書く                        | `describe_channel(name)`                                          |
| 5   | 過去の期間のunit, descriptionを直す                          | `describe_channel(cid)`                                           |
| 6   | 型の推定が外れた (数値の後に文字列が来た)                    | `replace_channel(name, T)` + `rejections` から再投入              |
| 7   | 全期間の型を変える (doubleで自動作成されたがintegerにしたい) | `replace_channel(name, 最初のts)`. 全行が移り, 古いcidは空になる  |
| 8   | 予定されたセンサー交換                                       | `replace_channel(name, 未来のT)`                                  |
| 9   | 既に済んだセンサー交換に後から気づいた                       | `replace_channel(name, 過去のT)`. `ts >= T` の行を移す            |
| 10  | 交換後に, 古いセンサーのデータが遅れて届く                   | 何もしない. 古いcidに入る                                         |
| 11  | replaceを取り消す, Tを間違えた                               | `merge_channel(新しいcid, 同じname)`. やり直す時はもう一度replace |
| 12  | nameの誤字, naming ruleの変更                                | `rename_channel(name)`. 送信側を先に変える                        |
| 13  | 1つの期間だけ別のnameにする (襲名)                           | `rename_channel(cid)`                                             |
| 14  | 送信側の設定ミスで別nameのchannelができ, データが入った      | `merge_channel(誤ったcid, 正しいname)`                            |
| 15  | テストやbugで作られたゴミchannel                             | `drop_channel(cid)`                                               |
| 16  | センサーの撤去, 運用終了                                     | 何もしない. 必要なら `describe_channel()` で記録                  |
| 17  | 撤去後, 同じnameで再設置                                     | 同じものなら何もしない. 別物なら8と同じ                           |
| 18  | 1つのnameに2つのセンサーが同時に書いていた                   | 対応しない. tsで分けられないので人間が解析する                    |

 - 6: 切り替えの前に `type_mismatch` で拒否された値は, `rejections.record` に元の入力がそのまま残っています. `SELECT insert_records(jsonb_agg(record)) FROM rejections WHERE ...` のように渡し直せます.
 - 7: 空になった古いcidは `drop_channel()` で消せます.
 - 12: `rename_channel()` の後も古いnameで送ってくるwriterがいると, 古いnameのchannelが新しく自動作成されます. 送信側のnameを先に変えてください.
 - 13: 古いセンサーの期間を別のnameに退避して, 同じnameを新しいセンサーに使う場合は, `replace_channel(name, T)` で期間を区切ってから, 古い期間を `rename_channel(古いcid, 'x.old')` で退避します. 古いセンサーのデータが古いnameのまま遅れて届いても, 新しいセンサーのchannelには入らず, `out_of_validity` で拒否されます. 先に退避してから新しいchannelを自動作成させると, 新しいchannelは全期間有効になるので, 遅れて届いた古いデータが新しいchannelに入ってしまいます.

#### ロック
`replace_channel()`, `rename_channel()`, `merge_channel()`, `drop_channel()` は, 実行中の書き込みが終わるのを待ち, 完了するまで新しい書き込みを待たせます.
どのchannelにデータが入るかを変える操作なので, 途中の書き込みが古い定義で振り分けられないようにするためです.
データを移さない場合は一瞬ですが, 大量のデータを移す場合や, 長い一括投入の最中に実行した場合は, その間, 通常の書き込みも止まるので注意してください.
`create_channel()` と `describe_channel()` は書き込みを止めません.

過去のデータを移す操作は, 移す行数に比例して時間がかかります.
1 秒周期のchannelでの目安です (2年分 60億行の入ったDB, Apple M4 Max).

| 操作                                       | 速さ         | 30日分 (260万行) | 1年分 (3150万行) |
| ------------------------------------------ | ------------ | ---------------- | ---------------- |
| `replace_channel()` (過去の `valid_from`)  | 約5万行/秒   | 43 ~ 53 秒       | 約10分 (見込み)  |
| `merge_channel()`                          | 約15万行/秒  | 17 秒            | 約4分 (見込み)   |

 - 止まっている間の書き込みは待たされ, 終わった後に書き込まれます. 試験では失われませんでした.
 - WALも多く出ます (`replace_channel()` の30日分で 約13 GB).
 - `drop_channel()` は測っていませんが, 行を `rejections` に移すので, `replace_channel()` と同じかそれ以上かかります.
 - 大きな移動は, DAQを止められる時に行ってください.

#### 変更履歴
`channels` の変更は, triggerで全て `channel_log` に記録されます (関数を通さない直接のSQLによる変更も含みます).
各行は, 変更したrole (`logged_by`, ログインしたrole), 時刻, 操作 (`insert`, `update`, `delete`), 変更前後の行 (`old`, `new`) を持ちます.
データを移す関数 (`replace_channel()`, `merge_channel()`, `drop_channel()`) は, 移した件数などを1行追加で記録します.
同じ呼び出しによる行は, 同じ `xact_id` を持ちます.
`raw_records` を直接変更した場合は記録されません.

#### 管理スクリプト
`utils/kl_admin.py` は, 日常の管理をコマンドラインで行うスクリプトです. SQLの全ての機能は網羅しません. それ以外の操作はSQLで行います.
`asyncpg` が必要です (Slowdashの環境に含まれます).

接続先は `--dsn` か, 環境変数 `KL_ADMIN_DB` (無ければ `KL_WRITER_DB`) で指定します.
```bash
export KL_ADMIN_DB=postgresql://kl_admin:PASSWORD@localhost:15432/kldb
```

| コマンド                                                | 内容                                                                           |
| ------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `list [文字列] [--unfilled]`                            | channelの一覧と最新値. nameに文字列を含むもの, unitかdescriptionが未記入のもの |
| `describe <name or cid> --unit U --description D`       | unit, descriptionを書く (`describe_channel()`)                                 |
| `create <name> [--type T] [--unit U] [--description D]` | channelを作る (`create_channel()`)                                             |
| `export [文字列] [--unfilled]`                          | channelの一覧をCSV (`name`, `type`, `unit`, `description`) で標準出力に書く    |
| `import <file> [--yes] [--create]`                      | CSVのunit, descriptionを書き込む                                               |
| `rejections [--since '1 day']`                          | 最近の拒否の集計 (status, nameごとの件数)                                      |

unit, descriptionをまとめて書く時は, CSVに書き出して, 表計算ソフトやeditorで埋めてから取り込みます.
```bash
python3 utils/kl_admin.py export --unfilled > channels.csv
# channels.csv を編集する
python3 utils/kl_admin.py import channels.csv          # 変更点を表示するだけ
python3 utils/kl_admin.py import channels.csv --yes    # 書き込む
```

 - `import` は, `--yes` を付けないと変更点を表示するだけで, 書き込みません. `--yes` の時は, 全ての変更を1つのtransactionで書き込みます.
 - CSVの値は書いたまま入ります. 空欄は `''` (unitなら単位の無い量) です.
 - `export` は未記入 (`NULL`) も空欄で書きます. `import` は, `export` した時と同じ行 (触っていない行) は飛ばし, 1か所でも変えた行は, 書いたままを書き込みます. 未記入の行のdescriptionだけを書いてunitを空欄のままにすると, unitは `''` になります (行ごとに確認済みにする, という扱いです).
 - `describe` は, 指定しなかったoption (`--unit` など) の項目を変えません.
 - nameは, そのnameの今のchannel (`valid_from` が最も新しいcid) を指します. 過去の期間のchannelは, `describe` でcidを指定します.
 - CSVにあって, DBに無いnameは飛ばします. `--create` を付けると, CSVの `type` (空欄なら `double`) で作ります. 事前にchannelを定義しておく一覧としても使えます.
 - `create` と `import --create` はwriterかadminで実行します. それ以外はmonitorでも実行できます (`describe_channel()` はmonitorにも許可されているため).

### Partition
`raw_records` は週ごと (UTCの月曜 00:00 が境界) にpartitionされます.
partitionは `insert_records()` が自分で作ります.

 - 書き込む週: 書き込むrecordの週のpartitionが無ければ, その場で作ります.
 - 次の週: 呼び出しのたびに, 現在の次の週のpartitionがあるかを確かめ, 無ければ作ります. このため, 週の始めの書き込みは, 通常は作成を待ちません.

作成は `CREATE TABLE ... (LIKE raw_records)` と `ALTER TABLE ... ATTACH PARTITION` の2段階で行うので, 作成中も他の読み書きを止めません.
(`CREATE TABLE ... PARTITION OF` は親table全体をロックし, 読み書きが全て止まります.)

人間や外部のscriptから先の分を作っておく場合は, `ensure_partitions(weeks)` を使います. 今週と, その先 `weeks` 週 (default: 4, 最大 10000) のpartitionを作り, 作成した数を返します.
```sql
SELECT ensure_partitions(52);   -- 1年先まで
```
空のpartitionは1つ 約64 kBです. ただし, partitionが多いほど `ts` の範囲を指定しないqueryは遅くなるので (後述の[viewを読む時の注意](#viewを読む時の注意)), 何年分も先に作る必要はありません.

同じpartitionを同時に作ろうとした場合は, 順番に処理されます.
default partitionは持ちません.
古いpartitionは永久に保存します. 将来archiveする場合は `DETACH PARTITION` で切り離せます.

### 最新値
最新値は `latest` viewで読みます. nameごとに1行です.

```sql
-- 現在値の一覧
SELECT name, ts, value, unit FROM latest WHERE name LIKE 'env.%';

-- 10分以上更新が止まっているchannel
SELECT name, ts FROM latest WHERE ts < now() - interval '10 minutes';
```

`value` は数値の型 (double, integer, boolean) の値をdoubleにしたもので, `records` と同じです. textとjsonの値は `value_text`, `value_jsonb` に入ります. integerの正確な値は `value_int` にもあります.

実体は `raw_latest` tableで, cidごとの最新の値を持ちます.
`insert_records()` の中で, 書き込んだrecordをcidごとにまとめてから更新するので, 1回の呼び出しでの更新は (recordの数ではなく) channelの数だけです.
`ts` が今の最新値より古い場合は更新しません.

`raw_records` から最新値を直接求めると, partitionごとにindexが分かれているため, 更新の止まったchannelでは全てのpartitionを遡ることになり, 遅くなります.
`raw_latest` はこれを避けるためのものです.
`raw_latest` は派生データなので, `rebuild_latest(cid)` で `raw_records` から作り直せます. cidを省略すると全てのchannelを作り直します (1万channelで 約0.2秒. その間は書き込みが止まります).
データを移す関数は, 関係するcidの `raw_latest` を自動で作り直します.

### Role

| role          | 用途                    | 権限                                                                                                 |
| ------------- | ----------------------- | ---------------------------------------------------------------------------------------------------- |
| `kl_admin`    | 管理者. 全objectのowner | 全て                                                                                                 |
| `kl_writer`   | DAQ, slowtask           | 書き込み関数, `create_channel()`, `describe_channel()`, `ensure_partitions()` の実行と全ての読み込み |
| `kl_monitor`  | Slowdashなどの監視      | 読み込みと `describe_channel()`. 短い `statement_timeout`, 接続数の上限                              |
| `kl_analyzer` | 人間による解析          | 読み込みと, 作業用schemaへの書き込み                                                                 |

4つともLOGIN roleです. `role_prefix` を変えると `kl` の部分が変わります.
`rejections` と `channel_log` は全てのroleが読めます.
`kl_admin` は `pg_read_all_stats` を持ち, cluster内の全てのsessionのqueryを見られます.
roleの設定はmembershipでは継承されないので, 別のLOGIN roleを作ってこれらのroleに所属させても, timeoutは効かないことに注意してください.

`kl_analyzer` の `search_path` は作業用schemaが先頭なので, schema名を付けずに作ったtableは作業用schemaに入ります.
作業用schemaに `records` など同じ名前のtableを作ると, viewが隠れることに注意してください.

### 設定
設定は種類ごとに以下に置かれます.
`settings_overview` viewで, 全ての設定を一覧できます (読むだけです. 変更はそれぞれの置き場所で行います).

| 種類                        | 項目                                                | 置き場所, 変更方法                              |
| --------------------------- | --------------------------------------------------- | ----------------------------------------------- |
| install時に決め, 以後は固定 | `schema`, `role_prefix`                             | `install.sql` の変数                            |
| storeの関数の振る舞い       | `max_past`, `max_future`                            | `settings` table (`UPDATE settings SET ...`)    |
| roleの設定                  | `statement_timeout`, 接続数の上限, `search_path`    | `ALTER ROLE ...`. 初期値は `install.sql` の変数 |
| PostgreSQL serverの設定     | `max_locks_per_transaction`, `max_connections` など | `postgresql.conf`                               |
| slowtask                    | `dsn`, `spool` など                                 | `SlowdashProject.yaml`                          |

storeの関数の振る舞いに関わる設定は, 全て `settings` table (1行) の列にします. 列ごとに型とCHECK制約を持つので, 不正な値は入りません.
`settings.schema_version` はschemaのversionで, 変更しないでください.
PostgreSQL自体の設定は二重管理にならないよう, tableには写さず, PostgreSQLの仕組みのまま変更します.

### 直接操作する場合
用意した関数で対応できない場合は, adminが直接SQLで `channels` や `raw_records` を操作します.
関数が保っている以下の不変条件を, 操作の後も保ってください.

 1. `raw_records` の全てのcidが `channels` に存在する (foreign keyが無いので, DBは検査しません).
 2. 各行の `ts` が, そのcidの有効期間 `[valid_from, 次のvalid_from)` の中にある.
 3. 各行で値が入っている列が, channelの型に対応する列である.
 4. `raw_latest` が, 各cidの `raw_records` の最新の行と一致する.
 5. 受け取ったデータを消さない. 行を消す時は, 先に `rejections` に移す.

手順の雛形です.
```sql
BEGIN;
SET LOCAL ROLE kl_admin;
SET LOCAL search_path = kl_store;
LOCK TABLE ONLY raw_records IN SHARE MODE;   -- 書き込みを止める. replace_channel() などと同じ

-- ここで UPDATE / DELETE / INSERT

SELECT rebuild_latest(cid) FROM ...;          -- 変更したcid
SELECT * FROM check_integrity();             -- 空であることを確認する
COMMIT;
```

`check_integrity(ts_from, ts_to)` は, 不変条件 1 ~ 4 を検査して, 違反を一覧で返します.
1 と 3 は `[ts_from, ts_to)` の範囲の `raw_records` を全て読みます. 省略すると全期間で, table全体を読む重い処理になります. 2 と 4 はindexだけで検査します.
`channels` の変更は `channel_log` に記録されますが, `raw_records` の直接の変更は記録されません.

### Performance, index
`raw_records` のindexは2つです.

 - `(cid, ts)` のunique index (B-tree). channelを指定するquery用. 重複の検出にも使います.
 - `ts` のBRIN index. 全channelを時間範囲で読むquery用. データはほぼ `ts` の順に入るのでよく効き, 大きさは1 partitionあたり数十kBです.

1行あたり, heap 約 60 B, index 約 37 B です (2年分 60億行で 554 GB).
`rejections` は `received_at` のBRIN indexを持ちます (最近の拒否を見るquery用).
`raw_records` から `channels` へのforeign keyは持ちません. cidの整合性は入り口の関数が保証します. (foreign keyがあると, partitionの作成時に `channels` がロックされ, channelの自動作成とdeadlockする可能性があります.)

#### 性能の目安
想定の規模 (1000 channel, 100 行/秒) の2年分 (60億行) を入れたDB (PostgreSQL 16, Apple M4 Max, memory 128 GB, SSD) で測りました.

 - 書き込み: 想定の負荷で, `insert_records()` の1回 (10 record) が 2.5 ~ 4 ms です. 上限は, 1接続で 約1.6万行/秒 (batch 10) ~ 4.4万行/秒 (batch 1000), 8接続で 約32万行/秒です.
 - Slowdashのplot (600点にresample. cacheが温まった状態):

   | channel         | 30日    | 1年    | 2年    |
   | --------------- | ------- | ------ | ------ |
   | 19 秒周期, 1つ  | 0.03 秒 | 0.4 秒 | 0.8 秒 |
   | 19 秒周期, 10個 | 0.35 秒 | 4 秒   | 8 秒   |
   | 1 秒周期, 1つ   | 0.6 秒  | 7 秒   | 14 秒  |

   cacheが冷えた状態では数倍かかります (1 秒周期の1年分で 約30秒).
   期間の全ての行を読んでresampleするので, 時間は期間の行数に比例します. 1 秒周期のchannelの長い期間は, monitorの `statement_timeout` (30秒) に近づきます.

#### viewを読む時の注意
viewはqueryの中に展開されるので, `name` と `ts` の条件はそのまま `raw_records` のindexとpartitionの選択に使われます.
ただし, `ts` の範囲を指定しないと, 全てのpartitionを読みます.
例えば「最新の10件」を範囲なしで求めると, viewはnameからcidをjoinで求めるため, そのchannelの全期間の行を読んでから並べ替えます.

queryは `SELECT * FROM` に続く部分です.

| query (最新10件)                                                                              | 時間 (200 channel, 4週間, 1600万行) |
| --------------------------------------------------------------------------------------------- | ----------------------------------- |
| `records WHERE name='x' ORDER BY ts DESC LIMIT 10`                                            | 410 ms (全期間に比例して遅くなる)   |
| `records WHERE name='x' AND ts > now() - interval '1 day' ORDER BY ts DESC LIMIT 10`          | 2.8 ms                              |
| `raw_records WHERE cid = (SELECT cid FROM channels WHERE name='x') ORDER BY ts DESC LIMIT 10` | 0.11 ms                             |

 - 通常は `ts` の範囲を指定します. Slowdashからのqueryは常に範囲を指定します.
 - 範囲が分からない場合 (止まったchannelなど) は, `latest` からcidを決めます.
   ```sql
   SELECT * FROM records
     WHERE cid = (SELECT cid FROM latest WHERE name = 'x')
     ORDER BY ts DESC LIMIT 10;
   ```
   cidが先に1つに決まるので, 新しいpartitionから順に読んで, 必要な行数で止まります. 止まったchannelでも, 期間の長さによらず速く読めます.
   `latest` のcidは, そのnameで一番新しい行を持つcidです. そのnameに複数のcidがある場合 (`replace_channel()` の後) は, そのcidの行だけが返ります. 期間は重ならないので違う行が返ることはありませんが, 切り替えの直後は件数が足りないことがあります.
   その場合は, cidごとに新しい方から読みます.
   ```sql
   SELECT r.* FROM (SELECT cid FROM channels WHERE name = 'x') c
    CROSS JOIN LATERAL (SELECT * FROM raw_records r WHERE r.cid = c.cid ORDER BY r.ts DESC LIMIT 10) r
    ORDER BY r.ts DESC LIMIT 10;
   ```
   Slowdashのqueryは常に `ts` の範囲を付けるので, この問題は起きません.

 - 現在値だけが欲しい場合は `latest` を使います.
 - 範囲の無いqueryは, 履歴が長いほど遅くなります. 2年分の試験では, 1 秒周期のchannel (6300万行) の範囲の無い最新1件は, monitorの `statement_timeout` (30秒) を超えました. その間heap全体を読むので, 通常の書き込みも数秒遅れました.
 - `ts` の範囲は, 時刻の値で書いてください (`ts > '2026-11-01 00:00+09'` など). `now()` を使う条件 (`ts > now() - interval '1 day'`) は, 実行時まで値が決まらないので, 計画時にはpartitionを絞れず, 範囲の無いqueryと同じく全てのpartitionを開いてロックします (30年分のpartitionで, 計画に 約0.25秒). Slowdashのqueryは時刻の値を埋め込むので, 問題ありません.

検討して採らなかった方法は, 後述の[採用しなかったこと](#採用しなかったこと)にあります.

#### ロック表
30年分のpartitionは約1560個になります.
計画時に `ts` の範囲が決まらないquery (範囲の無いquery, `now()` を使う条件) は, 全てのpartitionと, そのindexをロックします. 1回のqueryで partitionの数の約3倍で, 30年分では約4700個です.
ロックはtransactionの終わりまで持つので, psqlで `BEGIN` したままの接続は, ロックを持ち続けます.
PostgreSQLのロック表の大きさは, おおよそ `max_locks_per_transaction × max_connections` です. 足りなくなると, queryは `out of shared memory` で失敗します.
default (64 × 100 = 6400) では, このようなqueryが2本同時に走ると足りなくなるので, `max_locks_per_transaction` を大きめ (例えば 512) に設定してください (変更にはserverの再起動が必要です).

 - 512 で, 30年分のpartitionの状態で試すと, このようなqueryを同時に40本まで実行できました. 80本では半数が失敗しました. 30年の運用では, 1024 ~ 2048 にしてください.
 - `insert_records()` は, 接続ごとのロックの枠 (fast-path) に収まるので, ロック表が埋まっても通常の書き込みは失敗しませんでした. ただし, 新しいpartitionを作る時は, 共有のロック表を使います.

#### Queryの統計 (オマケ)
storeの動作には不要ですが, 遅いqueryを探す時に便利です.
PostgreSQL付属の `pg_stat_statements` (extension) は, 実行されたqueryを, 定数を除いた形ごとに集計します (回数, 合計時間, 平均時間, 読んだblock数など).
例えば, Slowdashのどのplotのqueryが重いか, `ts` の範囲を付け忘れたqueryが走っていないか, が分かります.

有効にするには, serverの起動時にlibraryを読み込む必要があります.
dockerのDBでは, `docker-compose.yaml` の `command` に `-c shared_preload_libraries=pg_stat_statements` を加えて, 作り直します (`docker compose up -d`). それ以外では, `postgresql.conf` の `shared_preload_libraries` に加えて, serverを再起動します.
その後, superuserでdatabaseに1回だけ以下を実行します.
```sql
CREATE EXTENSION pg_stat_statements;
```

合計時間の多いqueryの一覧です.
```sql
SELECT calls, round(total_exec_time) AS total_ms, round(mean_exec_time, 1) AS mean_ms,
       r.rolname, left(query, 80) AS query
FROM pg_stat_statements s JOIN pg_roles r ON r.oid = s.userid
ORDER BY total_exec_time DESC LIMIT 20;
```
集計は `SELECT pg_stat_statements_reset();` で0に戻せます.
`kl_admin` は全てのroleの統計を読めます (`pg_read_all_stats`). 他のroleは, 自分のqueryの統計だけを読めます.

#### 並行書き込み
同じデータを, 別々の接続から逆の順番で同時に送ると, deadlockで片方の呼び出し全体が失敗することがあります (spoolの再投入と, 別の再送が重なった場合など).
slowtaskは失敗したmessageをspoolに残すので, 再投入すれば失われません.


## Slowdashからの利用

### 配置
`SlowdashProject.yaml` に加える設定の例は `SlowdashProject_example.yaml` です ([Dash start](#dash-start)の2).

 - 数値のchannelは `records` の `value` を, json型のchannel (histogramなど) は `value_jsonb` を読みます.
 - `tags` を指定しないと, Slowdashはchannelの一覧を得るためにデータ全体を走査します. 必ず指定してください.
 - `kl_monitor` には `search_path` が設定されているので, schema名を付けずに `records` と書けます.
 - `@toolbox/kl_pg_store` は, Slowdashのinstall先の `toolbox/tasks/kl_pg_store/` のslowtaskを指します. Slowdashをdockerで動かす場合は, imageに `toolbox/` が含まれていなければ, このrepositoryの `toolbox/` を `/slowdash/toolbox` にmountします. 手順は次の[Slowdashをdockerで動かす](#slowdashをdockerで動かす)にあります.
 - slowtaskは `asyncpg` を使います. Slowdashのinstall時に `pg_config` があれば, `requirements.txt` に含まれます.
 - DBの接続先は, 環境変数 `KL_WRITER_DB`, `KL_MONITOR_DB` (PostgreSQLのURL) で与えます.

### Slowdashをdockerで動かす
DBはportを公開しているので, Slowdashのcontainerからも, 他のclientと同じく, host名 (またはIP address) と公開したport (default `15432`) で接続します.
containerの中の `localhost` はcontainer自身なので, `localhost:15432` は使えません.

自分のprojectのdirectory (`SlowdashProject.yaml` のあるところ) に, 以下の `docker-compose.yaml` を置きます.
```yaml
services:
  slowdash:
    image: slowproj/slowdash
    ports:
      - "18881:18881"
    volumes:
      - .:/project
      - /path/to/slowdash/toolbox:/slowdash/toolbox:ro   # このrepositoryの toolbox/
    environment:
      - KL_WRITER_DB=postgresql://kl_writer:PASSWORD@dbhost:15432/kldb
      - KL_MONITOR_DB=postgresql://kl_monitor:PASSWORD@dbhost:15432/kldb
```
```bash
docker compose up -d
```

 - `dbhost` はDBのhost名にします. DBが同じhostにある場合は, `host.docker.internal` を使い, Linuxでは `extra_hosts: ["host.docker.internal:host-gateway"]` も加えます.
 - imageには `toolbox/` が含まれていないので, このrepositoryの `toolbox/` をmountします. `/path/to/slowdash` は自分の環境のpathにします.
 - `KL_WRITER_DB`, `KL_MONITOR_DB` は, [Dash start](#dash-start)の2と同じです. `PASSWORD` は `\password` で設定したものにします.
 - spoolのファイル (`./kl_pg_store-spool.jsonl`) は, mountしたprojectのdirectoryに書かれます.

手元のSlowdash (このrepositoryのcheckout) を使う場合は, repositoryのtopの `Dockerfile` でimageを作り, `image` をそれに替えます.
```bash
cd /path/to/slowdash
docker build -t slowdash:local .
```
```yaml
    image: slowdash:local
```

 - imageには, build時の `app/`, `lib/` などが入ります. Slowdash本体を変更した時は, buildし直して `docker compose up -d` で作り直します.
 - `toolbox/` はimageに入らず, 上のようにmountしたものを使います. slowtask (`toolbox/tasks/kl_pg_store/`) の変更は, buildし直さずに, Slowdashの再起動 (`docker compose restart`) で反映されます.

### channelのページ
slowtask `kl_pg_store` は, HTML panel `kl_channels` を提供します.
以下の手順で表示します.

 1. Slowdashのhomeで, 新しいplot layoutを作ります (`New Plot Layout`).
 2. layoutの空いたところにmouseを置くと出る `Add a New Panel` から, `HTML Form` を選びます.
 3. HTML Fileに `kl_channels` を選び, `On Update` の `reload HTML` をonにします. ボタンを押した後に, ページが読み直されて結果が表示されます.
 4. layoutを保存しておくと, 次からはhomeの一覧から開けます.

slowtaskが動いていないと, `kl_channels` は選択肢に出ません.

ページでできることは以下です.

 - channelの作成: `create_channel()` を呼びます. 入力欄の値をそのまま書き込み, 空欄は `''` です. 既にあるnameを指定すると, 何も変えずにエラーを表示します (変える時は `Set` を使います).
 - channelの一覧: cid, name, `valid_from`, type, unit, description, 最新値 (doubleは有効数字6桁で表示), その `ts` と `inserted_at` を表示します. 最新値の時刻で, 更新の止まったchannelが分かります.
 - unit, descriptionの書き換え: `Set` で, その行の入力欄の値をそのまま書き込みます (`describe_channel()` をcidで呼びます). 空欄は `''` (unitなら単位の無い量) です. 未記入 (`NULL`) の欄には, 灰色で `unfilled` と表示されます.

HTML panelはJavaScriptを使えず, 状態を持てないので, 絞り込み, 並べ替え, ページの条件はslowtaskが1つだけ持ちます. 同時に開いている全員に共通です.
`reload HTML` がoffだと, ボタンを押してもページが読み直されず, 何も変わらないように見えます.
ページの実装は `kl_channel_page.py` にあり, slowtaskはこれを読み込むだけです.

なお, formの値はSlowdashが一度JSONとして解釈するので, 紛らわしい値は変わってしまいます.
descriptionに `1.50` と入れると `1.5` に, unitに `null` と入れると `None` になる, 既知の問題があります.
将来的に, Slowdashがサポートする仕組みの中でシンプルに解決できることを期待しています.

関数はslowtaskの中で `kl_writer` の接続で実行されるので, Slowdashの画面を開ける人は誰でもchannelを書き換え, 作成できます.

slowtaskの `parameters` は以下です.

| parameter | default                   | 内容                                  |
| --------- | ------------------------- | ------------------------------------- |
| `dsn`     | (必須)                    | `kl_writer` で接続するPostgreSQLのURL |
| `schema`  | `kl_store`                | `install.sql` に指定したschema        |
| `spool`   | `kl_pg_store-spool.jsonl` | DBに書き込めなかったmessageの保存先   |

### slowtaskの動作
1つのSlowMesh messageにつき, `insert_records()` を1回呼びます.
`DataPacket` の値は, そのままJSONの値として送ります. 型の推定と変換はDB側が行います.
numpyの値は, scalarはPythonの数値やboolに, 配列はlistに変換してから送ります (`np.float32(1.5)` は `1.5`, `np.array([1, 2])` は `[1, 2]`).
TimeSeries形式の `DataPacket` は, 時刻ごとのrecordに展開して送ります. channelのnameは, fieldが `x` ならtagそのもの, それ以外なら `<tag>.<field>` です.
これは文書の形 (`t` が配列) のmessageの場合です. 今のslowpyの `DataPacket(TimeSeries)` は `t` と `start` を落とすので, 時刻ごとには展開できません. fieldが `x` なら, 受信時刻に配列の値を持つ1つのrecordとして保存されます. それ以外のfieldだけなら, 次の `DataPacket` の形でないmessageとして扱います.

`DataPacket` の形でないmessage (例えば `{"env.temp": 24.2}`. 正しくは `{"env.temp": {"t": ..., "x": 24.2}}`. dictでも, `x` も配列の `t` も無いもの) も捨てずに, `value` を持たないrecordとして送り, `invalid_record` として `rejections` に元の形のまま残します.

拒否されたrecordは, (とりあえず今は) slowtaskのlogに出力します (DBの `rejections` にも保存されています).

DBに書き込めなかった場合 (DBの停止など), messageを `spool` に指定したファイルにJSON Linesで追記します.
`t` の無い値は, spoolに書く時に受信時刻を `ts` として補います (補わないと, 再投入した時刻で保存されるためです).
DBの復旧後, 以下で再投入します.
```bash
python3 utils/replay_spool.py postgresql://kl_writer:PASSWORD@localhost:15432/kldb kl_pg_store-spool.jsonl
```
再投入中もslowtaskはspoolへの追記を続けられます. 再投入に失敗したmessageはspoolに戻されます.
slowtaskの追記と再投入の開始 (spoolのrename) は, `<spool>.lock` のファイルのロック (`flock`) で順番に行うので, 再投入の途中に追記されたmessageも失われません. このロックはlocalのfilesystem (dockerのbind mountを含む) で効きます. NFS上にspoolを置かないでください.
spoolへの書き込み (再投入に失敗したmessageを戻す時も) は, `fsync` してから次に進むので, 電源断でも失われません.
再投入が途中で止まった場合に残るファイル (`<spool>.replaying-*`) は, 次の再投入で先に処理されます.
同じデータを重複して再投入しても, `duplicate` として拒否されるだけで, 二重には保存されません.
spoolの1行は `insert_records()` の入力そのもの (recordのJSON配列) なので, 必要なら直接編集してから再投入できます. DBが受け付けない行は, spoolに残り続けます.


## 採用しなかったこと

 - summary table: 例えば週のsummary tableは, `(cid, week)` ごとに件数, 最小, 最大, 平均などを持つtableと, それを作る関数で作れます.
   必要な時間幅や, 遅れてくるデータの量, 更新頻度が実験ごとにバラバラで, 実装も容易なのでここでは対応しません.
   `raw_records` から作れる派生データにすること, 書き込みの経路に手を入れないことが重要だと思います.
   遅れて届いたデータや, `insert_record_by_cid()` で補ったデータで過去の週が古くなりますが, 前回以降の `inserted_at` を持つ行を探せば, 作り直す `(cid, week)` が分かります.
   行はほぼ `inserted_at` の順に入るので, `inserted_at` のBRIN indexを足せば, 小さいindexで探せます.
 - 単位変換: 例えば, naming ruleの最後の部分を単位にする (と物理量も推測できる) というアイデアをとれば, 何かしらスマートなことが実装できそうですが, それらはユーザーのwrapperに譲ります.
   ここでは, naming ruleはユーザーの自由です (それでも, 何かしらの規則を持つことを強くおすすめします).
   名前に単位を含んでいなくても, `records` は行ごとにその時点のcidの `unit` を返すので, 途中でunitが変わったnameも, 行ごとに変換できます.
 - `latest` の `ts` を上限にするviewでの高速化: `ts <= (最新のts)` は結果を変えない条件ですが, 最新より古い全期間を読むことは変わらず, 速くなりません.
   速くなるのは下限ですが, 下限 (例えば `最新のts - 1 day`) は `LIMIT` を前提にした推測で, viewからは `LIMIT` が見えないので作れません.
 - `ts` のB-tree index: 測定して, あまりメリットがなかったので入れていません.
 - plot用の関数, 便利なtrigger, stored procedure: 過度に複雑になると, かえってユーザーが環境に応じて自由にいじくり回すのを妨げると考え, 入れていません (triggerはlog用途にだけ採用).
 - 古い週のデータへの自動的なCLUSTER: 単一channel, 長い時間範囲の時に得をして, 短い時間範囲, 複数channelで損をするはずです.
   後からどうとでもできるので, 採用を見送っています.
