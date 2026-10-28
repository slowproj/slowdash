---
title: 周辺ツールのチートシート
---

# このページについて
SlowDash を使う際によく必要になる周辺ツール（YAML、pyenv / venv、ネットワーク、バックグラウンド実行と自動起動、リレーショナルデータベース、Docker / Docker Compose / Docker Swarm）について、要点とよく使うコマンドをまとめたものです．各ツールの入門ではなく、「一度は使ったことがあるが、細かいところを忘れた」ときに参照することを想定しています．詳しくは各ツールの公式ドキュメントを参照してください．この文書は Claude によって作成されました．


# YAML
SlowDash のプロジェクト設定ファイル（`SlowdashProject.yaml`）と `docker-compose.yaml` は YAML で記述します．

## 書き方

```yaml
# コメント（行頭、または空白の後の # 以降）
name: QuickTour              # key: value（コロンの後に空白が必要）
title: "SlowDash: Test"      # 「: 」や「 #」を含む値は引用符で囲む

data_source:                 # 入れ子はインデント（スペースのみ、タブは不可）
  url: sqlite:///SlowStore.db

ports:                       # リスト
  - "18881:18881"
  - "5432:5432"

channels:                    # マップのリスト
  - name: ch00
    unit: K
  - name: ch01
    unit: mbar

tags: [a, b, c]              # インライン形式のリスト
opts: {width: 10, height: 5} # インライン形式のマップ

script: |                    # 複数行文字列（改行を保持）
  line 1
  line 2
command: >                   # 複数行文字列（改行を空白に置換）
  bash -c "echo hello"
```

## 引っかかりやすい点
- インデントの幅は揃っていれば何文字でもよいが、同じ階層では揃える．タブ文字はエラーになる．
- 値は自動的に型が推測される．文字列として扱いたいものは引用符で囲む：
  - `yes`, `no`, `on`, `off`, `true`, `false` は真偽値になる（Python の PyYAML の場合）
  - `0644` のように 0 で始まる数字は 8 進数として解釈されることがある
  - `22:22` のようなコロン区切りの数字は 60 進数の数値として解釈されることがある（ポート指定は常に `"22:22"` のように引用符で囲むのが安全）
  - 値が空の場合（`key:` だけ）は `null` になる
- 同じキーを2回書いてもエラーにならず、後の値で上書きされることが多い．

## 確認方法
意図どおりに読み込まれているかは、JSON に変換して表示すると確認できます（`pyyaml` が必要．SlowDash の venv には入っています）．

```console
$ python -c 'import sys,yaml,json; print(json.dumps(yaml.safe_load(open(sys.argv[1])), indent=2))' SlowdashProject.yaml
```

`docker-compose.yaml` の場合は `docker compose config` で、変数展開後の最終的な設定を表示できます．


# Python の環境：pyenv と venv

| | 管理するもの | 使う場面 |
|---|---|---|
| pyenv | Python 本体（インタプリタ）のバージョン | OS 標準の Python が古い（EOL）、または特定のバージョンが必要なとき |
| venv | パッケージ（`pip install` するもの）の置き場所 | プロジェクトごとに依存パッケージを分離したいとき（SlowDash では標準） |

両者は独立していて、併用できます．pyenv で選んだ Python を使って venv を作る、というのが典型的な組み合わせです．

## venv

```console
$ python3 -m venv venv              # カレントディレクトリに venv/ を作成
$ source venv/bin/activate          # 有効化（シェルごと、ターミナルを開くたびに必要）
(venv) $ pip install numpy          # この venv の中にだけインストールされる
(venv) $ pip list                   # インストール済みパッケージの一覧
(venv) $ pip install -r requirements.txt
(venv) $ deactivate                 # 無効化
```

有効になっているかの確認：

```console
$ echo $VIRTUAL_ENV                 # venv のパスが表示されれば有効
$ which python                      # .../venv/bin/python を指していれば有効
```

要点：

- 削除はディレクトリごと消すだけ（`rm -rf venv`）．
- 有効化しなくても、`venv/bin/python script.py` のように直接指定すればその venv で実行される（cron や systemd から実行するときに便利）．
- venv は作成時の Python 本体へのリンクを持っている．元の Python を削除・更新したり、venv のディレクトリを移動したりすると壊れるので、その場合は作り直す．
- Debian / Ubuntu では `python3-venv` パッケージが別になっていることがある（`sudo apt install python3-venv`）．

SlowDash との関係：ネイティブインストールの `make` は、SlowDash のディレクトリに `venv/` を作ります．`slowdash-activate-venv` は `source $SLOWDASH_DIR/venv/bin/activate` の別名です．

## pyenv
インストール（Linux / WSL）：

```console
$ curl -fsSL https://pyenv.run | bash
```

（macOS では `brew install pyenv`．）

続けて `~/.bashrc` に以下を追加し、`source ~/.bashrc` するか、新しいターミナルを開きます．

```bash
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
```

pyenv は Python をソースからビルドするので、事前にビルドに必要なライブラリを入れておきます（Ubuntu の場合．他の OS は [pyenv Wiki](https://github.com/pyenv/pyenv/wiki#suggested-build-environment) を参照）．

```console
$ sudo apt install build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
    libsqlite3-dev libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
```

これが不足していると、ビルドは成功しても `ssl` や `sqlite3` モジュールが使えない Python ができることがあります（警告はビルド時に表示されます）．

よく使うコマンド：

```console
$ pyenv install --list | grep '^ *3\.'   # インストール可能なバージョン一覧
$ pyenv install 3.12.9                   # インストール
$ pyenv versions                         # インストール済みの一覧
$ pyenv version                          # 現在有効なバージョンと、その設定元
$ pyenv global 3.12.9                    # ユーザーのデフォルトを設定
$ pyenv local 3.12.9                     # このディレクトリ以下だけ設定（.python-version ファイルが作られる）
$ pyenv uninstall 3.12.9
```

## 組み合わせ：pyenv の Python で venv を作る

```console
$ cd PATH/TO/SLOWDASH
$ pyenv local 3.12.9          # このディレクトリでは python3 が 3.12.9 になる
$ rm -rf venv                 # 古い Python で作った venv があれば削除
$ make                        # venv が 3.12.9 で作られる
```

一度 venv を作れば、その後は pyenv の設定に関係なく venv の Python が使われます．ただし、venv の元になった pyenv のバージョンを `pyenv uninstall` すると venv は壊れます．


# ネットワーク
SlowDash はブラウザから HTTP で接続して使います（標準のポートは 18881）．SlowDash 自体にはセキュリティ機能がほとんどないので、ファイアウォールの内側で使い、外部からは VPN、SSH トンネル、またはリバースプロキシを経由して接続するのが前提です．

## 調査に使うコマンド

| コマンド | 用途 |
|---|---|
| `ip -br addr` | 自分の IP アドレスの一覧 |
| `ip route` | ルーティングテーブル（`default via ...` がデフォルトゲートウェイ） |
| `ip route get ADDRESS` | 指定した宛先へ、どのインターフェース・ゲートウェイを通って出ていくか |
| `ping -c 5 HOST` | 到達できるかと、往復の遅延時間（RTT） |
| `tracepath HOST`、`traceroute HOST` | 経路上のルーターと、各区間までの遅延 |
| `mtr HOST` | 経路の各区間の遅延とパケットロスを継続的に表示 |
| `getent hosts NAME`、`dig NAME` | 名前解決の確認（`getent` は `/etc/hosts` も含めた、実際にプログラムが使う結果） |
| `sudo ss -tlnp` | 待ち受けている TCP ポートと、そのプロセス |
| `ss -tn` | 確立している TCP 接続 |
| `nc -zv HOST PORT` | 指定したポートに TCP で接続できるか |
| `curl -v http://HOST:18881/` | HTTP での接続を詳細表示 |
| `iperf3 -s`（相手側）、`iperf3 -c HOST` | 2 台の間の帯域の測定 |
| `sudo tcpdump -i any port 18881` | 実際に流れているパケットの観察 |

足りないコマンドは、`sudo apt install iputils-ping iputils-tracepath traceroute mtr-tiny dnsutils netcat-openbsd iperf3 tcpdump` でインストールできます．

HTTP の応答時間の内訳（接続、最初の 1 バイトが返るまで、全体）は、`curl` で測れます：

```console
$ curl -o /dev/null -s -w 'connect: %{time_connect}  first byte: %{time_starttransfer}  total: %{time_total}\n' http://HOST:18881/
```

要点：

- `ping` に応答がなくても、到達できないとは限らない（ICMP がファイアウォールで止められていることが多い）．特定のポートに接続できるかは `nc -zv` で確認する．
- 待ち受けアドレスが `0.0.0.0`（または `*`）なら全てのネットワークから、`127.0.0.1` なら同じマシンからだけ接続できる．`sudo ss -tlnp` で確認できる．
- 遠隔地からの表示が遅い場合、帯域よりも往復の遅延（RTT）が効いていることが多い．`ping` の RTT が数十 ms を超えるなら、リバースプロキシで HTTP/2 にする、あるいはデータベースのミラーと SlowDash を遠隔地側に置く（[レプリケーション](#データの複製レプリケーションpostgresql-mysql)）と改善することがある．

## SSH トンネル
ファイアウォールの内側の SlowDash に、SSH 経由で接続します．

```console
$ ssh -N -L 18881:localhost:18881 USER@SERVER                 # 手元の localhost:18881 → SERVER の localhost:18881
$ ssh -N -J USER@GATEWAY -L 18881:localhost:18881 USER@SERVER  # ゲートウェイ（踏み台）を経由する場合
```

ブラウザで `http://localhost:18881` を開きます．`-N` はコマンドを実行せずにトンネルだけを張るオプションです．逆向きに、内側のマシンから外側のマシンにポートを公開するには `-R` を使います（[レプリケーション](#データの複製レプリケーションpostgresql-mysql) の例を参照）．

よく使う設定は、`~/.ssh/config` に書いておくと `ssh slowdash` だけで接続できます．

```
Host slowdash
    HostName SERVER
    User USER
    ProxyJump USER@GATEWAY
    LocalForward 18881 localhost:18881
```

## ファイアウォール（ufw）
Ubuntu では、ファイアウォールの設定に `ufw` を使います（RHEL 系では `firewall-cmd`）．

```console
$ sudo ufw status verbose                    # 現在の状態と規則
$ sudo ufw default deny incoming             # 外からの接続は既定で拒否
$ sudo ufw default allow outgoing            # 外への接続は既定で許可
$ sudo ufw allow OpenSSH                     # SSH を許可（有効化する前に必ず！）
$ sudo ufw enable                            # 有効化

$ sudo ufw allow from 192.168.1.0/24 to any port 18881 proto tcp   # 特定のネットワークからだけ許可
$ sudo ufw allow from 203.0.113.5 to any port 5432 proto tcp       # 特定のホスト（例：DB のミラー）からだけ許可
$ sudo ufw allow 443/tcp                     # HTTPS を全体に許可（リバースプロキシ）

$ sudo ufw status numbered                   # 番号付きで規則を表示
$ sudo ufw delete 3                          # 番号で規則を削除
$ sudo ufw insert 1 deny from 198.51.100.7   # 先頭に規則を挿入
$ sudo ufw reload
$ sudo ufw disable
```

要点：

- リモートから SSH で作業している場合、SSH を許可する前に `ufw enable` すると、そのまま締め出される．
- 規則は上から順に評価され、最初に一致したものが適用される．
- SlowDash のポート（18881）は、研究室のネットワークなど必要な範囲だけに許可する．リバースプロキシを使う場合は、18881 は外部に開けず、443（と、HTTPS へ転送するための 80）だけを開ける．データベースのポート（PostgreSQL 5432、MySQL 3306）も、接続が必要なホストだけに許可する．
- 拒否された接続のログは `/var/log/ufw.log` に記録される（`sudo ufw logging on`）．
- 設定後は、別のマシンから `nc -zv HOST PORT` で、開いているべきポートだけが開いていることを確認する．

### Docker と ufw
Docker で公開したポート（`docker run -p` や Compose の `ports:`）は、ufw の規則を迂回して外部から接続できてしまいます．Docker が ufw より先に評価されるファイアウォール規則を直接追加するためです．

- 同じマシンからだけ接続できればよい場合は、`127.0.0.1` を付けて公開する：`-p 127.0.0.1:18881:18881`（Compose では `"127.0.0.1:18881:18881"`）．
- リバースプロキシも同じ Compose の中で動かす場合は、SlowDash に `ports:` を書く必要はない（サービス名で接続できる）．公開するのはリバースプロキシのポートだけにする．

## リバースプロキシと HTTPS
SlowDash は暗号化されていない HTTP/1.1 で通信します．外部から接続させる場合は、前段に Nginx や Apache などの Web サーバーを置き、そこで HTTPS に乗せ換えます（リバースプロキシ）．

```
ブラウザ ── HTTPS (443) ──▶ リバースプロキシ ── HTTP (18881) ──▶ SlowDash
                            （Nginx / Apache）                   （外部からは直接接続させない）
```

これにより、次のことができます．

- 通信の暗号化（HTTPS）
- HTTP/2 による高速化（遠隔地からの表示で特に効果がある）
- ポート番号のない URL（`https://HOST/slowdash/`）
- Basic 認証の追加（パスワードを守るために HTTPS が必須）

HTTPS には、サーバーの証明書が必要です．所属機関の証明書、Let's Encrypt（`certbot`、外部から接続できるホスト名が必要）、あるいは試験用の自己署名証明書（ブラウザに警告が出る）を使います．

設定方法は [Project Setup の「Using a Reverse Proxy Server」](ProjectSetup.html#using-a-reverse-proxy-server) と [SlowDash を使ってみるの「リバースプロキシ」](FirstStep-JP.html#リバースプロキシ) を、Docker Compose での動作例は `ExampleProjects/ReverseProxy` を参照してください．


# バックグラウンド実行と自動起動
`slowdash` のようなサーバープロセスは、ターミナルを閉じたりログアウトしたりしても動き続ける必要があり、本番運用ではマシンの起動時に自動で起動するようにします．

| 方法 | ログアウト後も動く | 起動時に自動で起動 | 異常終了時の再起動 | ログ | 向いている用途 |
|---|---|---|---|---|---|
| tmux / screen | ○ | × | × | 画面で見る | 開発・試験、一時的な運用 |
| nohup | ○ | × | × | ファイル | 一時的な運用 |
| cron `@reboot` | ○ | ○ | × | ファイル | 手軽な自動起動 |
| `/etc/rc.local` | ○ | ○ | × | ファイル | 古い方法（現在は systemd を推奨） |
| systemd | ○ | ○ | ○ | `journalctl` | ネイティブ環境での本番運用 |
| Docker | ○ | ○ | ○ | `docker logs` | Docker 環境での本番運用 |

以下の例では、`slowdash` コマンドを絶対パスで指定しています．`bin/slowdash` は自分で SlowDash の venv を有効にするので、venv を事前に有効化する必要はありません．

## tmux / screen
ターミナルの画面ごとバックグラウンドに残しておき、後から再接続できます．画面の出力をそのまま見られるので、開発中や試験運用に便利です．

| 操作 | tmux | screen |
|---|---|---|
| 名前を付けて開始 | `tmux new -s slowdash` | `screen -S slowdash` |
| 切り離す（プロセスは動き続ける） | `Ctrl-b` → `d` | `Ctrl-a` → `d` |
| 一覧 | `tmux ls` | `screen -ls` |
| 再接続 | `tmux attach -t slowdash` | `screen -r slowdash` |
| 開始と同時に切り離す | `tmux new -d -s slowdash 'COMMAND'` | `screen -dmS slowdash COMMAND` |
| 終了 | `tmux kill-session -t slowdash` | `screen -S slowdash -X quit` |

## nohup
ログアウトしても終了しないようにして、バックグラウンドで実行します．

```console
$ nohup /PATH/TO/SLOWDASH/bin/slowdash --port=18881 --project-dir=/PATH/TO/PROJECT > slowdash.log 2>&1 &
$ pgrep -af slowdash      # 動いているか確認（プロセス番号が表示される）
$ kill PID                # 停止
```

## cron の @reboot
`crontab -e` で、自分のユーザーの crontab に次の 1 行を追加すると、マシンの起動時に実行されます．root 権限は不要です．

```
@reboot /PATH/TO/SLOWDASH/bin/slowdash --port=18881 --project-dir=/PATH/TO/PROJECT >> /PATH/TO/slowdash.log 2>&1
```

cron の環境では `PATH` などがログイン時と異なるので、コマンドやファイルは絶対パスで指定します．

## /etc/rc.local
起動時に root 権限で実行されるスクリプトです．古い方法で、Ubuntu では標準では存在しませんが、作成すれば systemd 経由で実行されます．

```bash
#!/bin/sh
su - USER -c '/PATH/TO/SLOWDASH/bin/slowdash --port=18881 --project-dir=/PATH/TO/PROJECT >> /PATH/TO/slowdash.log 2>&1 &'
exit 0
```

- 実行権限が必要（`sudo chmod +x /etc/rc.local`）．
- root で実行されるので、`su - USER -c` で一般ユーザーとして実行する．終了しないプロセスは、最後に `&` を付けてバックグラウンドにする．

## systemd
現在の Linux の標準的な方法です．異常終了時の自動再起動やログの管理も systemd が行います．次の内容のファイルを `/etc/systemd/system/slowdash.service` として作成します．

```ini
[Unit]
Description=SlowDash
After=network-online.target
Wants=network-online.target
# 同じマシンのデータベースを使う場合は、その後に起動する：
# After=network-online.target postgresql.service

[Service]
Type=simple
User=USER
WorkingDirectory=/PATH/TO/PROJECT
ExecStart=/PATH/TO/SLOWDASH/bin/slowdash --port=18881
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```console
$ sudo systemctl daemon-reload              # サービスファイルを作成・変更したら実行
$ sudo systemctl enable --now slowdash      # 自動起動を有効にして、すぐに起動
$ systemctl status slowdash                 # 状態と最新のログ
$ journalctl -u slowdash -f                 # ログを表示（-f で追跡）
$ sudo systemctl restart slowdash           # 再起動（設定を変更したときなど）
$ sudo systemctl stop slowdash              # 停止
$ sudo systemctl disable slowdash           # 自動起動を無効にする
```

root 権限がない場合は、ユーザーのサービスとして登録することもできます．ファイルを `~/.config/systemd/user/slowdash.service` に置き（`User=` の行は削除し、`WantedBy=default.target` にする）、`systemctl --user enable --now slowdash` とします．ログアウト中やマシンの起動時にも動かすには、`loginctl enable-linger USER` が必要です（管理者に依頼）．

## Docker
Docker のコンテナは、もともとバックグラウンドで実行できます．再起動ポリシーを指定すると、異常終了時やマシンの起動時に自動で起動します．

```console
$ docker run -d --restart unless-stopped -p 18881:18881 -v $(pwd):/project slowproj/slowdash
```

Docker Compose では、各サービスに `restart: unless-stopped` を書き、`docker compose up -d` で起動します．

| 再起動ポリシー | 動作 |
|---|---|
| `no`（既定） | 自動で起動しない |
| `on-failure` | 異常終了したときだけ再起動 |
| `always` | 常に再起動（手動で停止しても、マシンの起動時には起動する） |
| `unless-stopped` | 常に再起動（ただし手動で停止したものは、マシンの起動時にも起動しない） |

マシンの起動時に Docker 自体が起動するようになっている必要があります（`sudo systemctl enable docker`．通常はインストール時に有効になっています）．


# リレーショナルデータベース：PostgreSQL / MySQL / SQLite
SQL の文法ではなく、時系列データを記録・表示するときに 3 つのデータベースで違いが出る点をまとめます．

| | PostgreSQL | MySQL | SQLite |
|---|---|---|---|
| 形態 | サーバー | サーバー | 1 つのファイル（サーバー不要） |
| 同時アクセス | 多数の読み書きに対応 | 多数の読み書きに対応 | 書き込みは同時に 1 つ．既定の設定では書き込み中の読み出しが待たされる（WAL モードで改善） |
| 向いている用途 | 本番運用 | 本番運用（既存のシステムで使われていることが多い） | 試験、小規模、1 台で完結する用途 |

## 接続とテーブルの確認

| 操作 | PostgreSQL（`psql`） | MySQL（`mysql`） | SQLite（`sqlite3`） |
|---|---|---|---|
| 接続 | `psql -h HOST -U USER DB` | `mysql -h HOST -u USER -p DB` | `sqlite3 FILE.db` |
| テーブル一覧 | `\dt` | `SHOW TABLES;` | `.tables` |
| テーブルの定義 | `\d TABLE` | `SHOW CREATE TABLE TABLE;` | `.schema TABLE` |
| インデックス一覧 | `\di` | `SHOW INDEX FROM TABLE;` | `.indexes TABLE` |
| 実行時間の表示 | `\timing on` | 常に表示される | `.timer on` |
| 終了 | `\q` | `exit` | `.quit` |

データベースを Docker Compose で動かしている場合は、コンテナ内のクライアントを使えます（例：`docker compose exec postgres psql -U USER DB`）．SQLite のクライアントは別にインストールが必要なことがあります（`sudo apt install sqlite3`）．

## データ型

| | PostgreSQL | MySQL | SQLite |
|---|---|---|---|
| 64 bit 浮動小数点 | `DOUBLE PRECISION` | `DOUBLE`（`REAL` も同じ） | `REAL` |
| 32 bit 浮動小数点 | `REAL` | `FLOAT` | なし（すべて 64 bit） |
| 整数 | `INTEGER`（32 bit）、`BIGINT`（64 bit） | `INT`（32 bit）、`BIGINT`（64 bit） | `INTEGER`（最大 64 bit） |
| 文字列 | `TEXT`、`VARCHAR(n)` | `VARCHAR(n)`、`TEXT` | `TEXT` |
| JSON | `JSONB`、`JSON` | `JSON` | `TEXT`（JSON 関数あり） |
| NaN、Inf | 格納できる | 格納できない | NaN は NULL になる |
| 型の扱い | 厳密 | 厳密（strict モード、既定で有効） | 緩い（宣言と違う型の値も格納できる） |

注意点：

- `REAL` の意味がデータベースによって違う．PostgreSQL の `REAL` は 32 bit で、有効数字は約 7 桁しかない．UNIX 時刻（約 1.7×10⁹）を 32 bit 浮動小数点に入れると、分解能が 128 秒になってしまう．時刻を数値で入れる列は、64 bit 浮動小数点（PostgreSQL では `DOUBLE PRECISION`、MySQL では `DOUBLE`）か `BIGINT` にする．
- MySQL の `TEXT` 型の列は、そのままではインデックスに使えない（先頭の文字数の指定が必要）．チャンネル名など、検索に使う列は `VARCHAR(n)` にする．

## 時刻とタイムゾーン

| | PostgreSQL | MySQL | SQLite |
|---|---|---|---|
| タイムゾーン付き | `TIMESTAMP WITH TIME ZONE`（`TIMESTAMPTZ`） | `TIMESTAMP` | なし |
| タイムゾーンなし | `TIMESTAMP` | `DATETIME` | 日時の文字列を `TEXT` に入れる |
| UNIX 時刻（数値） | `DOUBLE PRECISION`、`BIGINT` | `DOUBLE`、`BIGINT` | `REAL`、`INTEGER` |
| 秒未満の精度 | マイクロ秒 | 既定では秒まで．`TIMESTAMP(6)` などで指定 | 格納の仕方による |
| 接続のタイムゾーンの確認 | `SHOW timezone;` | `SELECT @@session.time_zone;` | なし |
| UNIX 時刻 → 日時 | `to_timestamp(x)` | `FROM_UNIXTIME(x)` | `datetime(x, 'unixepoch')` |
| 日時 → UNIX 時刻 | `extract(epoch FROM t)` | `UNIX_TIMESTAMP(t)` | `strftime('%s', t)` |

要点：

- 「タイムゾーン付き」の型も、タイムゾーン自体は保存しない．書き込むときに接続のタイムゾーン設定で UTC に変換して保存し、読み出すときに接続のタイムゾーンに変換して返す．そのため、同じデータでも接続の設定によって表示される時刻が変わる（指している時点は同じ）．
- 「タイムゾーンなし」の型は、書かれた日時をそのまま保存し、どのタイムゾーンの時刻かは記録しない．書き込む側と読み出す側で解釈を合わせる必要がある．夏時間の切り替わりでは、時刻の重複や欠落が起きる．
- MySQL の `TIMESTAMP` は 2038-01-19 03:14:07 UTC までしか扱えない（2038 年問題）．`DATETIME` にはこの制限はないが、タイムゾーンなしの型．
- MySQL の `TIMESTAMP` / `DATETIME` は、精度を指定しないと秒未満が丸められる．
- MySQL でタイムゾーン名（`'Asia/Tokyo'` など）を使うには、サーバーにタイムゾーン表が読み込まれている必要がある．`'+09:00'` のようなオフセットでの指定は常に使える．
- SQLite の `CURRENT_TIMESTAMP` や `datetime('now')` は UTC の日時文字列を返す．
- UNIX 時刻（64 bit 浮動小数点）で記録すれば、タイムゾーンも 2038 年問題もなく、3 つのデータベースで同じように扱える．

SlowDash でそれぞれの型を指定する方法は、[Data Binding](DataBinding.html) を参照してください．

## インデックス
時系列データの典型的な読み出しは次の形です（SlowDash がプロットのために発行するクエリもこの形）．

```sql
SELECT timestamp, channel, value FROM data
WHERE channel IN ('ch00', 'ch01') AND timestamp >= 開始時刻 AND timestamp < 終了時刻
ORDER BY timestamp;
```

これには `(channel, timestamp)` の複合インデックスが有効です．複合インデックスでは、等号で絞り込む列を先に、範囲で絞り込む列を後に並べます．`(timestamp, channel)` の順だと、指定した時間範囲の全チャンネルのデータを読んでからチャンネルで絞り込むことになり、チャンネル数が多いと遅くなります．

### PostgreSQL

```sql
CREATE INDEX CONCURRENTLY data_channel_timestamp ON data (channel, timestamp);
ANALYZE data;
```

- `CONCURRENTLY` を付けると、書き込みを止めずにインデックスを作成できる（その分時間がかかる．トランザクション内では使えない）．
- `... ON data (channel, timestamp) INCLUDE (value)` とすると、インデックスだけで結果を返せる（Index Only Scan）ので、さらに速くなることがある．
- 時刻順に追記されるだけの非常に大きなテーブルでは、BRIN インデックスも有効（B-tree よりはるかに小さい）：`CREATE INDEX data_timestamp_brin ON data USING brin (timestamp);`

### MySQL（InnoDB）
InnoDB のテーブルは、主キーの順に格納されます．このため、主キーの選び方が性能に大きく影響します．

```sql
CREATE INDEX data_channel_timestamp ON data (channel, timestamp);
-- または、主キーそのものを (channel, timestamp) にする（テーブル全体が再構築される）
ALTER TABLE data DROP PRIMARY KEY, ADD PRIMARY KEY (channel, timestamp);
ANALYZE TABLE data;
```

- 主キーを `(channel, timestamp)` にすると、チャンネルごとのデータが連続して格納されるので、読み出しが速い．
- 主キー以外のインデックスを使う場合、`value` を読むためにテーブル本体を引き直す必要がある．インデックスを `(channel, timestamp, value)` にすれば、これが不要になる．

### SQLite
SQLite でも、インデックスは他のデータベースと同じように効きます．

```sql
CREATE INDEX data_channel_timestamp ON data (channel, timestamp);
ANALYZE;
PRAGMA journal_mode=WAL;
```

- `PRAGMA journal_mode=WAL` にすると、書き込み中でも読み出しが待たされなくなる．設定はファイルに保存されるので、一度実行すればよい．ネットワークファイルシステム（NFS など）上のファイルでは使えない．

### チャンネル一覧の取得
`SELECT DISTINCT channel FROM data` は、そのままでは全行を読むので、大きなテーブルでは遅くなります．

- MySQL と SQLite は、`channel` で始まるインデックスがあれば、インデックスを飛ばし読みして高速に処理する．
- PostgreSQL は飛ばし読みをしないので、再帰クエリで同じことをする：

```sql
WITH RECURSIVE t(channel) AS (
    SELECT MIN(channel) FROM data
  UNION ALL
    SELECT (SELECT MIN(channel) FROM data WHERE channel > t.channel) FROM t WHERE t.channel IS NOT NULL
)
SELECT channel FROM t WHERE channel IS NOT NULL;
```

SlowDash では、このようなクエリを `time_series` の `tags: sql:` に指定できます（[Data Binding](DataBinding.html) を参照）．

## クエリのパフォーマンス測定
### 実行計画の確認
クエリの前に `EXPLAIN` を付けると、インデックスが使われているかを確認できます．

| | コマンド | 全件を読んでいる（遅い） | インデックスを使っている |
|---|---|---|---|
| PostgreSQL | `EXPLAIN ANALYZE SELECT ...;` | `Seq Scan` | `Index Scan`、`Index Only Scan`、`Bitmap Index Scan` |
| MySQL | `EXPLAIN ANALYZE SELECT ...;` | `Table scan` | `Index range scan`、`Index lookup` |
| SQLite | `EXPLAIN QUERY PLAN SELECT ...;` | `SCAN data` | `SEARCH data USING INDEX ...` |

例：SQLite で 20 チャンネル × 20,000 点のテーブルに `(channel, timestamp)` のインデックスを追加すると、次のように変わります．

```
インデックスなし：SCAN data, USE TEMP B-TREE FOR DISTINCT            （DISTINCT：20 ms）
インデックスあり：SCAN data USING COVERING INDEX data_channel_timestamp （DISTINCT：0.1 ms 未満）
```

- `EXPLAIN ANALYZE` はクエリを実際に実行して時間を測る（`INSERT` や `DELETE` なら実際に変更される）．`EXPLAIN` だけなら実行しない．MySQL の `EXPLAIN ANALYZE` はバージョン 8.0.18 以降．
- 2 回目以降はデータがメモリにキャッシュされて速くなるので、何回か実行して比べる．PostgreSQL では `EXPLAIN (ANALYZE, BUFFERS)` とすると、ディスクからの読み出し量も表示される．
- 統計情報が古いと、インデックスがあっても使われないことがある．大量のデータを追加したときやインデックスを作成したときは `ANALYZE`（MySQL では `ANALYZE TABLE`）を実行する．

### SlowDash が発行している SQL を調べる
SlowDash を `--logging=debug` 付きで起動すると、実行した SQL がログに出力されます．これに `EXPLAIN ANALYZE` を付けて実行すると、どこが遅いかを調べられます．

```console
$ slowdash --port=18881 --logging=debug
```

### 遅いクエリの記録
指定した時間より長くかかったクエリを、サーバーのログに記録できます．

```sql
-- PostgreSQL：1 秒以上かかったクエリを記録
ALTER SYSTEM SET log_min_duration_statement = '1s';
SELECT pg_reload_conf();

-- MySQL：1 秒以上かかったクエリを記録（ログファイルの場所は SELECT @@slow_query_log_file; で確認）
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 1;
```

### テーブルの大きさ

```sql
-- PostgreSQL（psql では \dt+ や \di+ でも表示できる）
SELECT pg_size_pretty(pg_total_relation_size('data'));

-- MySQL
SELECT table_name, data_length, index_length FROM information_schema.tables WHERE table_schema = DATABASE();
```

SQLite はファイルの大きさがそのままデータベースの大きさです．どのデータベースも、データを削除しただけではファイルは小さくなりません．領域を解放するには、PostgreSQL では `VACUUM FULL`、MySQL では `OPTIMIZE TABLE`、SQLite では `VACUUM` を実行します（いずれも実行中はテーブルがロックされます）．

## 大規模データ：パーティショニング（PostgreSQL / MySQL）
連続測定のテーブルは増え続けるだけなので、何年分も溜まるとインデックスが大きくなり、古いデータの削除（`DELETE`）にも非常に時間がかかるようになります．パーティショニングでは、1 つのテーブルを時間範囲（例えば 1 か月）ごとの小さなテーブル（パーティション）に分けて格納します．読み書きは、これまでどおり 1 つのテーブルとして行えます．

- 時刻で範囲を指定したクエリは、該当するパーティションだけを読む（partition pruning．`EXPLAIN` で確認できる）．
- 古いデータの削除は、パーティションごと削除するだけで済み、一瞬で終わる．削除せずに切り離して、別に保存することもできる．
- 目安としては、テーブルが数十 GB、数億行を超える、あるいは古いデータを定期的に削除したい場合に検討する．パーティションの数が多すぎる（数千以上）と、逆にクエリの準備に時間がかかる．
- 主キーやユニークキーには、パーティションの分割に使う列（時刻の列）を含める必要がある．`(channel, timestamp)` ならそのまま使える．

### PostgreSQL

```sql
CREATE TABLE data (
    timestamp TIMESTAMPTZ NOT NULL,
    channel VARCHAR(100) NOT NULL,
    value DOUBLE PRECISION,
    PRIMARY KEY (channel, timestamp)
) PARTITION BY RANGE (timestamp);

-- パーティションの作成（親テーブルの主キー・インデックスは自動的に作られる）
CREATE TABLE data_2026_11 PARTITION OF data FOR VALUES FROM ('2026-11-01 00:00+00') TO ('2026-12-01 00:00+00');

-- 古いパーティションを削除、または切り離して通常のテーブルとして残す
DROP TABLE data_2024_01;
ALTER TABLE data DETACH PARTITION data_2024_01;
```

- 該当するパーティションがないデータの `INSERT` はエラーになる．測定を止めないために、パーティションは前もって作っておく（cron などで定期的に作る）．
- パーティションの作成・削除を自動化する拡張として pg_partman がある．時系列データ向けの拡張 TimescaleDB を使うと、パーティショニング（chunk）、圧縮、古いデータの削除が自動で行われ、テーブルは通常の SQL で読み書きできる．
- 親テーブルには `CREATE INDEX CONCURRENTLY` が使えない．

### MySQL

```sql
CREATE TABLE data (
    timestamp DATETIME(6) NOT NULL,   -- UTC で書き込む前提
    channel VARCHAR(100) NOT NULL,
    value DOUBLE,
    PRIMARY KEY (channel, timestamp)
)
PARTITION BY RANGE COLUMNS (timestamp) (
    PARTITION p2026_11 VALUES LESS THAN ('2026-12-01'),
    PARTITION pmax VALUES LESS THAN (MAXVALUE)
);

-- 新しいパーティションの追加（pmax を分割する）
ALTER TABLE data REORGANIZE PARTITION pmax INTO (
    PARTITION p2026_12 VALUES LESS THAN ('2027-01-01'),
    PARTITION pmax VALUES LESS THAN (MAXVALUE)
);

-- 古いパーティションの削除
ALTER TABLE data DROP PARTITION p2026_11;
```

- 分割に使える列の型に制限がある．`DATETIME` と整数型は使えるが、`DOUBLE` は使えない（UNIX 時刻で記録する場合は `BIGINT` にする）．`TIMESTAMP` の場合は `PARTITION BY RANGE (UNIX_TIMESTAMP(timestamp))` とする．
- `MAXVALUE` のパーティションを作っておけば、パーティションの追加が遅れても `INSERT` はエラーにならない．

## データの複製：レプリケーション（PostgreSQL / MySQL）
レプリケーションは、データベースへの書き込みを別のサーバー（ミラー）にほぼリアルタイムでコピーし続ける仕組みです．一般のデータベースシステムでは、サーバー故障時に処理を引き継ぐ（可用性）ことが主な目的とされますが、SlowDash の典型的な用途ではこれはあまり重要ではありません（データベースサーバーが止まるときは、たいてい他にもっと大きな問題が起きています）．むしろ、次の目的で使います．

- **データ消失への備え**：記録したデータを、常に別のサーバーにも保持しておく．
- **遠隔地からのアクセス**：研究室など別の場所にミラーを置き、遠隔のユーザー（とその SlowDash）はミラーに接続する．実験サイトとの回線を毎回経由しないので速い．
- **セキュリティ**：外部からのアクセスをミラーに限定し、記録を行うサーバーは外部に公開しない．ミラーには必要なデータテーブルだけを複製する．

### 「バックアップ」として守れるもの

| データの失われ方 | レプリケーションで守れるか |
|---|---|
| ディスクの故障、サーバーの損失、火災・災害 | 守れる（別の場所にコピーがある） |
| 誤った `DELETE` や `DROP`、プログラムの誤りによる書き換え | 通常は守れない（ミラーにも反映される）．ただし、PostgreSQL の論理レプリケーションで追記（`INSERT`）だけを複製すれば、削除はミラーに反映されない |
| 過去のある時点の状態に戻す | できない．必要なら、定期的なダンプ（`pg_dump`、`mysqldump`）やファイルシステムのスナップショットを併用する |

連続測定のデータは追記されるだけのことが多いので、「追記だけを複製する遠隔ミラー」は、データ消失に対する実用的なバックアップになります．

### 方式

| | PostgreSQL 論理レプリケーション | PostgreSQL ストリーミングレプリケーション | MySQL レプリケーション |
|---|---|---|---|
| 複製の単位 | 指定したテーブル | サーバー全体（全データベース、ユーザー情報を含む） | サーバー全体（ミラー側で絞り込める） |
| 複製する操作 | 選べる（追記だけ、など） | すべて | すべて |
| ミラー側 | 通常のデータベース（独自のテーブルやインデックスも置ける） | 読み出し専用 | 通常のデータベース（読み出し専用に設定するのが普通） |
| 記録側とミラーのバージョン | 異なってもよい | 同じメジャーバージョンが必要 | ミラーは同じか新しいバージョン |
| 向いている用途 | 遠隔ミラー、外部公開用 | 同じサイト内の予備 | 両方 |

### 共通の注意点
- 非同期レプリケーション（既定）で十分．ミラーは数秒程度遅れて追従する．同期レプリケーションにすると、ミラーや回線が止まったときに記録側の書き込みも止まってしまう．
- どの方式も、ミラー側から記録側のサーバーに接続する．記録側を外部に公開したくない場合は、記録側から SSH トンネルを張る（`ssh -N -R 15432:localhost:5432 MIRROR_HOST` とすると、ミラー側の `localhost:15432` が記録側の PostgreSQL につながる）か、VPN を使う．複製用のユーザーの権限は最小限にし、ファイアウォールではミラーの IP アドレスだけを許可する．
- ミラーや回線が止まっている間、記録側には未送信の更新ログが溜まり、ディスクを消費する．再開すれば自動的に追いつくが、長期間止めたままにしない．
- テーブル定義の変更（`ALTER TABLE` など）は、論理レプリケーションでは複製されない．ミラー側でも同じ変更を行う．

### PostgreSQL：論理レプリケーション（遠隔ミラー）

```sql
-- 記録側（postgresql.conf で wal_level = logical を設定し、再起動しておく）
CREATE ROLE mirror WITH REPLICATION LOGIN PASSWORD '...';
GRANT SELECT ON data TO mirror;
CREATE PUBLICATION data_pub FOR TABLE data WITH (publish = 'insert');   -- 追記だけを複製

-- ミラー側（同じ定義のテーブルを先に作っておく）
CREATE SUBSCRIPTION data_sub
    CONNECTION 'host=RECORDING_HOST port=5432 dbname=DB user=mirror password=...'
    PUBLICATION data_pub;
```

- 最初に既存のデータがすべてコピーされ、その後は追記が随時反映される．
- 記録側の `pg_hba.conf` では、ミラーの IP アドレスから、そのデータベースへの通常の接続を許可する（論理レプリケーションの接続には `replication` の指定は使われない）．
- 状態の確認：ミラー側で `SELECT * FROM pg_stat_subscription;`、記録側で `SELECT slot_name, active FROM pg_replication_slots;`
- 記録側では、ミラー用のレプリケーションスロットが作られ、ミラーが受け取るまで更新ログが保持される．ディスクを使い切らないように、`max_slot_wal_keep_size` で上限を設定しておく．
- 記録側のテーブルがパーティショニングされている場合は、`WITH (publish = 'insert', publish_via_partition_root = true)` とすると、ミラー側は 1 つの通常のテーブルで受けられる．記録側で古いパーティションを削除しても、ミラーには残る（記録側は直近のデータだけ、ミラーは全期間、という運用ができる）．

### PostgreSQL：ストリーミングレプリケーション（同じサイト内の予備）

```console
# ミラー側で実行：記録側のデータ全体をコピーし、ミラーとして設定する（-R）
$ pg_basebackup -h RECORDING_HOST -U replicator -D /var/lib/postgresql/data -R -P
```

- 事前に、記録側でレプリケーション用のユーザーを作り（`CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD '...';`）、`pg_hba.conf` にミラーからの `replication` 接続を許可する設定を書いておく．
- 状態の確認：記録側で `SELECT client_addr, state, replay_lag FROM pg_stat_replication;`、ミラー側で `SELECT pg_is_in_recovery();`（ミラーなら `true`）．

### MySQL

```sql
-- 記録側で実行：レプリケーション用のユーザーを作成
CREATE USER 'replicator'@'%' IDENTIFIED BY '...';
GRANT REPLICATION SLAVE ON *.* TO 'replicator'@'%';

-- ミラー側で実行（記録側とミラーの両方で gtid_mode=ON, enforce_gtid_consistency=ON を設定しておく）
CHANGE REPLICATION FILTER REPLICATE_DO_TABLE = (DB.data);   -- data テーブルだけを反映する場合
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST='RECORDING_HOST', SOURCE_USER='replicator', SOURCE_PASSWORD='...',
    SOURCE_AUTO_POSITION=1, GET_SOURCE_PUBLIC_KEY=1;
START REPLICA;
```

- `CHANGE REPLICATION SOURCE TO` と `START REPLICA` はバージョン 8.0.23 以降の書き方（それ以前は `CHANGE MASTER TO` と `START SLAVE`）．`GET_SOURCE_PUBLIC_KEY=1` は、SSL を使わずに MySQL 8 の標準の認証方式で接続するために必要．
- 記録側とミラーで、それぞれ異なる `server_id` を設定する．既存のデータは、事前に `mysqldump` や clone プラグインでミラーにコピーしておく．
- テーブルの絞り込み（`REPLICATE_DO_TABLE`）はミラー側で行われる．記録側からは全テーブルの更新ログが送られてくるので、外部に出るデータそのものを限定したい場合には向かない．また、削除も含めてすべての操作が反映される．
- 状態の確認：ミラー側で `SHOW REPLICA STATUS\G`．`Replica_IO_Running` と `Replica_SQL_Running` が `Yes` で、`Seconds_Behind_Source` が遅れの秒数．
- ミラーには `super_read_only=ON` を設定して、誤って書き込まないようにしておく．
- 記録側の更新ログ（binlog）の保持期間は `binlog_expire_logs_seconds`（既定は 30 日）．ミラーがこれより長く止まると、最初からコピーし直しになる．

# Docker
SlowDash は Docker なしでも使えます．Docker を使う場合は、ホストに Python 環境を用意せずに SlowDash やデータベースを動かせます．

| 用語 | 意味 |
|---|---|
| イメージ | 実行環境（OS のファイル、ライブラリ、プログラム）をまとめたもの．`slowproj/slowdash`、`postgres:16` など．`:` 以降はタグ（バージョン） |
| コンテナ | イメージから起動された実行中のインスタンス |
| ボリューム / バインドマウント | コンテナの外にデータを置く仕組み．コンテナを削除しても残る |
| ポートの公開 | ホストのポートをコンテナのポートに転送する |

## docker run

```console
$ docker run --rm -p 18881:18881 -v $(pwd):/project slowproj/slowdash
```

| オプション | 意味 |
|---|---|
| `-p HOST:CONTAINER` | ホストのポートをコンテナのポートに転送 |
| `-v HOST_PATH:CONTAINER_PATH` | ホストのディレクトリをコンテナ内にマウント（ホスト側は絶対パス） |
| `-v NAME:CONTAINER_PATH` | 名前付きボリュームをマウント（Docker が管理する領域にデータを保存） |
| `-e NAME=VALUE` | 環境変数を設定 |
| `--rm` | 停止したらコンテナを自動削除 |
| `-d` | バックグラウンドで実行 |
| `--name NAME` | コンテナに名前を付ける |
| `-it` | 対話的に実行（シェルを使うとき） |

## よく使うコマンド

```console
$ docker ps                       # 実行中のコンテナ一覧（-a で停止中も）
$ docker logs -f CONTAINER        # ログを表示（-f で追跡）
$ docker exec -it CONTAINER bash  # 実行中のコンテナ内でシェルを起動
$ docker stop CONTAINER
$ docker rm CONTAINER
$ docker images                   # ローカルにあるイメージ一覧
$ docker pull IMAGE:TAG           # イメージを取得・更新
$ docker rmi IMAGE                # イメージを削除
$ docker system prune             # 停止中のコンテナや未使用のイメージ等をまとめて削除
```

## 引っかかりやすい点
- Linux では、`docker` コマンドに root 権限が必要．毎回 `sudo` を付けるか、ユーザーを `docker` グループに追加する（`sudo usermod -aG docker $USER` の後、ログインし直す）．`docker` グループのユーザーは実質的に root 権限を持つことに注意．
- コンテナ内の `localhost` はコンテナ自身を指す．ホストで動いているデータベース等に接続するには `host.docker.internal` を使う（Linux では `--add-host=host.docker.internal:host-gateway` が必要）．
- `-p` で公開したポートは、ufw のファイアウォール規則を迂回して外部から接続できてしまう（[Docker と ufw](#docker-と-ufw) を参照）．
- コンテナ内のプロセスが root で動いていると、バインドマウントしたディレクトリに作られたファイルはホスト上で root の所有になる（データベースのデータディレクトリをバインドマウントした場合など）．
  - SlowDash のコンテナでは、起動時にマウントされた `/project` ディレクトリの所有者（UID / GID）を調べ、同じ ID のユーザーで SlowDash を実行するようになっている．このため、SlowDash が作るファイルはプロジェクトディレクトリの所有者のものになる．ID を明示したい場合は、環境変数 `USER_ID` と `GROUP_ID` で指定できる．
  - ただし `docker exec` で入ったシェルは root で動くので、そこで作ったファイルは root の所有になる．SlowDash と同じユーザーで実行するには `docker exec -it -u slowuser CONTAINER bash` とする．

## イメージの更新と古いイメージの削除
`:latest` などのタグは自動では更新されません．新しいバージョンを使うには、`docker pull`（Compose では `docker compose pull`）でイメージを取得してから、コンテナを起動し直します．

`docker pull` は古いイメージを削除しません．新しいイメージがタグを引き継ぎ、古いイメージはタグなし（`<none>`）として残るので、更新を繰り返すとディスクを圧迫します．

```console
$ docker images                   # イメージ一覧．タグが <none> のものが古いイメージ
$ docker system df                # イメージ、コンテナ、ボリュームのディスク使用量
$ docker image prune              # タグなしのイメージをすべて削除
$ docker image prune -a           # コンテナから使われていないイメージをすべて削除（次回使うときは再取得になる）
$ docker rmi IMAGE_ID             # 個別に削除（IMAGE_ID は docker images で表示される）
```

停止中のコンテナが使っているイメージは削除できません．`docker ps -a` で確認し、不要なコンテナを `docker rm` してから削除します．


# Docker Compose
複数のコンテナ（例：SlowDash とデータベース）の構成を `docker-compose.yaml` に書いておき、まとめて起動・停止する仕組みです．

## docker-compose.yaml

```yaml
services:
  postgres:                              # サービス名（他のコンテナからはこの名前でアクセスできる）
    image: postgres:16
    environment:
      - POSTGRES_USER=slowdash
      - POSTGRES_PASSWORD=slowdash
    volumes:
      - postgres-data:/var/lib/postgresql/data   # 名前付きボリューム
    healthcheck:                         # 起動完了の判定方法
      test: ["CMD-SHELL", "pg_isready -U slowdash"]
      interval: 10s
      retries: 5
    restart: unless-stopped              # 異常終了やホスト再起動時に自動で再起動

  slowdash:
    image: slowproj/slowdash
    ports:
      - "18881:18881"
    volumes:
      - ./slowdash.d:/project            # バインドマウント（相対パスは docker-compose.yaml の場所から）
    environment:
      - DB_URL=postgresql://slowdash:${DB_PASSWORD:-slowdash}@postgres:5432/slowdash
    depends_on:
      postgres:
        condition: service_healthy       # postgres の healthcheck が通ってから起動
    restart: unless-stopped

volumes:
  postgres-data:
```

要点：

- 同じ `docker-compose.yaml` のサービス同士は、サービス名をホスト名として通信できる（上の例では `postgres:5432`）．`ports` はホストから接続する場合にだけ必要．
- `${VAR}` や `${VAR:-DEFAULT}` は、シェルの環境変数か、同じディレクトリの `.env` ファイルから展開される．パスワード等は `.env` に書いて、`.env` は git に入れないのが一般的．
- `depends_on` は起動の順序だけを制御する．相手の準備が完了するまで待つには `condition: service_healthy` と `healthcheck` を組み合わせる．

## よく使うコマンド
`docker-compose.yaml` のあるディレクトリで実行します．

```console
$ docker compose up               # 起動（Ctrl-C で停止）
$ docker compose up -d            # バックグラウンドで起動
$ docker compose ps               # 状態を表示
$ docker compose logs -f SERVICE  # ログを表示
$ docker compose exec SERVICE bash
$ docker compose restart SERVICE
$ docker compose down             # 停止してコンテナを削除（名前付きボリュームは残る）
$ docker compose down -v          # 名前付きボリュームも削除（データベースのデータが消える）
$ docker compose pull             # イメージを更新（その後 up で反映．古いイメージは docker image prune で削除）
$ docker compose up --build       # build: で指定したイメージを作り直して起動
$ docker compose config           # 変数展開後の設定を表示（設定の確認に便利）
```

`docker-compose`（ハイフンあり）は旧バージョンのコマンドで、すでにサポートが終了しています．現在は `docker compose`（スペース）を使います．


# Docker Swarm
複数のホストにまたがってコンテナを配置・管理する仕組みです．Docker に標準で含まれていて、`docker-compose.yaml` とほぼ同じ形式のファイルを使います．1台のホストで動かすだけなら Docker Compose で十分です．Swarm が役に立つのは、たとえば次のような場合です．

- SlowDash、データベース、各機器のリーダーなどを複数のホストに分けて配置し、1つの設定ファイルで管理したい
- どのホストからでも同じポートでサービスにアクセスしたい
- パスワード等を secret として管理したい

## クラスタの構成

```console
manager$ docker swarm init --advertise-addr MANAGER_IP   # manager ノードでクラスタを作成
manager$ docker swarm join-token worker                  # worker 追加用のコマンドを表示
worker$  docker swarm join --token TOKEN MANAGER_IP:2377 # worker ノードで実行
manager$ docker node ls                                  # ノード一覧
```

ノード間で TCP 2377、TCP/UDP 7946、UDP 4789 が通信できる必要があります．

## スタックの配置
Swarm では、`docker-compose.yaml` で定義したサービス群を「スタック」として配置します．コマンドは manager ノードで実行します．

```console
$ docker stack deploy -c docker-compose.yaml STACK      # 配置（変更後の再適用も同じコマンド）
$ docker stack ls
$ docker stack services STACK                           # サービス一覧とレプリカ数
$ docker stack ps STACK                                 # 各コンテナがどのノードで動いているか
$ docker service logs -f STACK_SERVICE                  # サービス名は「スタック名_サービス名」
$ docker service update --force STACK_SERVICE           # サービスを再起動
$ docker stack rm STACK                                 # スタックを削除
```

## Compose との違い

```yaml
services:
  slowdash:
    image: slowproj/slowdash
    ports:
      - "18881:18881"
    volumes:
      - /srv/slowdash/project:/project
    deploy:                              # Swarm でのみ有効
      replicas: 1
      placement:
        constraints:
          - node.hostname == daq-server  # このノードで動かす
```

- `deploy:` セクションが有効になる（レプリカ数、配置するノード、再起動ポリシー等）．
- `build:` は無視される．イメージはレジストリから取得できるか、各ノードにあらかじめ存在する必要がある．
- `depends_on` は無視される．起動順序は保証されないので、各サービスは接続先が準備できるまで再試行する必要がある（Swarm はデフォルトで、終了したコンテナを自動的に再起動する）．
- バインドマウントのホスト側パスは、そのコンテナが実際に動くノード上に存在する必要がある．データやプロジェクトディレクトリを使うサービスは `placement` でノードを固定するのが簡単．
- `ports` で公開したポートは、クラスタ内のどのノードの IP からでもアクセスできる（routing mesh）．
- `.env` ファイルは自動では読み込まれない．変数展開が必要な場合は、事前にシェルで読み込む（`set -a; source .env; set +a`）．
- データベースや SlowDash のように状態を持つサービスは、通常 `replicas: 1` にする．


# 参考リンク
- YAML: [yaml.org](https://yaml.org/)
- venv: [Python ドキュメント](https://docs.python.org/ja/3/library/venv.html)
- pyenv: [GitHub](https://github.com/pyenv/pyenv)
- PostgreSQL: [ドキュメント](https://www.postgresql.org/docs/)
- MySQL: [リファレンスマニュアル](https://dev.mysql.com/doc/refman/8.4/en/)
- SQLite: [ドキュメント](https://www.sqlite.org/docs.html)
- Docker / Docker Compose / Docker Swarm: [Docker Docs](https://docs.docker.com/)
