# 認証と権限管理

## 方針
- 認証(Authentication)を通った場合には全ての操作ができると想定する．ここが唯一のセキュリティ境界．
- セキュリティ機能（認証）は自作しない．
- Role による権限管理(Authorization)は意図しない誤操作を防ぐためのもの．
- SlowTask による個別操作（PubSub と RPC）は，明示的に禁止されなければ許可．

## 認証 (Authentication)
- まずは Slowlette 組み込みの基本認証（＋プロキシによる HTTPS）で user を取得
- 本番ではリバースプロキシから取得できるように
  - Nginx 経由で外部認証に接続できる（OAuth2, SSO, etc.）
  - 特定端末向けクライアント証明書もできる (mTLS)
  - ユーザー名は X-Remote-User ヘッダで取得（クライアントの偽装に注意）
    - SlowDash が通常使うポート (18881) はファイアウォールで閉じておく（`127.0.0.1` bind だけに依存しない；docker で間違えるから）
    - ホストPCが信用できない場合は，SlowDash の uvicorn を外付けにして，Nginx とは UNIX Socket でつなげることも可能（コード変更なし）
    - Nginx と SlowDash を同一 Docker Compose で動かせば，偽プロキシの問題はかなり回避できる
  - CSRF 対策も Nginx（＋認証プロキシ） に入れておく（SlowDash では，状態変更 API は POST のみ）
  - Nginx ならレートリミットも設定できる
- 認証を有効にしていない場合（リバースプロキシを通していない場合）の user は `nobody`

- さらにその外側を VPN で囲んでも良いかも

- SlowMesh:
  - SlowMQ を使う場合，
    - 外部からは Slowlette (リバースプロキシ)を通らないと SlowMesh には到達できない
    - さらに WebSocket だけを遮断すれば，SlowMQ だけが切られる（データストリーミングは SSE）
  - NATS などの外部バックボーンを使う場合は，外部アクセスを閉じるか，そのシステムが認証をする

## 権限 (Authorization)
- user_name への user_role の割当は Slowdash 設定ファイル
  - user_name / user_role に特殊文字は受け入れない
  - user_name にも user_role にも階層構造はなし
  - user_role は先頭に `#` をつけて user_name と合わせ，user にする．
    - 例： operator と admin の role を持った sanshiro は `user = [ 'sanshiro', '#operator', '#admin' ]`
  - 将来拡張: role に包含構造をもたせられる．user 構築時点で展開しておく
    - 例： `"roles": [ { 'name': 'expert', 'includes': [ 'operator', 'analyzer' ] ]`
  - 許可は `allowed is None or set(user) & set(allowed)` 演算．
- Slowlette ミドルウェアで slowlette.Request に user を追加
  - 全てのウェブリクエストで user 情報が使える
- Web API `api/config` のリプライにユーザー情報を含めてブラウザにも通知
  - ブラウザ側も user がわかる（偽装可）

## 利用
### サーバー側
- ユーザーレイアウト（slowdash/slowplot）一覧では，それぞれの見せる・見せないを role で選択（表示のみ・直接取得は可能）
- スタートページも２種類用意？
- コマンド実行では，role を確認（強制）
- タスクコントロールは SlowdashProject.yaml で個別に実行権限を指定（強制）
- スクリプト編集権限は？
  - 登録タスクに関しては SlowdashProject.yaml で指定できる
  - 自由作成スクリプトはあまり制限したくない（解析目的もある）
    - まずは一律の「作成許可」ロール（一律禁止，一律許可は利用者次第）
    - 将来的には:
      - Mesh への publish を許さない（LocalMesh に接続）にすれば，間違えてコマンドを送ることはない
        - [ `data.>` および  `alarm.>` ] への publish だけを許可とかもできるかも
      - 解析サンドボックスを作成することも検討（Jupyter コンテナとか．不用意なスクリプト実行からの保護．セキュリティ目的ではない）
- ユーザー名は操作ログにも入る

### ブラウザ側
- どこかにユーザー名・ロール名を表示
- できるのは表示管理のみ．ブラウザはその気になればどんなコマンドでもサーバーに送れる．操作許可はサーバー側．
- Canvas パネルではページ単位で操作許可，さらに個別デバイスでオーバーライド可能
- HTML パネルは何もしない（HTMLを含むレイアウト自体を表示するかどうかでコントロール）

### Task 側
- SlowMesh のヘッダに user 情報を付加（偽装可，Task スクリプトからは自己申告）
- Task 内一律なら SlowdashProject.yaml から許可設定
- ハンドラごとなら `@mesh.on('control.HV.>', allowed='#operator')`, `@mesh.export(allowed='...')`
- 拒否に例外を投げれば SlowMesh がエラーレスポンスを返す


## 中の人が悪意を持っている場合（想定外の想定）
### 結論
- 測定系サブネットを分離してファイアウォールを入れる
- 権限奪取を止める（SlowTask の user 自己申告を変更できなくする）
  - SlowDash にバグがないなら：
    - スクリプト編集機能を SlowdashProject.yaml で無効にする（デフォルト）
    - プロキシで WebSocket を通さないようにして，外部からの SlowMesh アクセス（外部の SlowTask からのアクセス）を止める（例ではそうなっている）
  - 完全にするなら:
    - SlowDash (Nginx) を外に見せない．サブネット内部へのアクセスは ssh のみ
    - 隔離 SlowDash の外(DMZ)に別の SlowDash を走らせて，隔離 SlowDash から DMZ SlowDash にモニタデータだけを HTTP POST する
    - データベースも（必要なデータだけ）別にコピーしておく
    - 外部から操作が必要なら自分で ssh トンネルを掘る

---

### 現時点の構成
- SlowDash の設定ファイル（SlowdashProject.yaml / docker-compose.yaml）はログインしないと編集できない
- SlowTask の「自己申告」を変えるにはスクリプトの編集が必要
  - SlowTask スクリプトの Web からの編集は権限管理とは独立に機能無効にできる（デフォルトでは無効になている）
  - 外の SlowTask から SlowMesh (SlowMQ) への直接接続は WebSocket 経由．プロキシで WebSocket を通さなくすれば，これができなくなる（例ではそうなっている）．データストリーミングは SSE なので影響されない
- 解析スクリプトは，例の中では Jupyter の独立コンテナ内での実行．コンテナ内でソフトウェアを自分でセットアップしない限り，基本的にはデータ読み出ししかできない．この解析機能も無効にできる（デフォルトで無効）．

### 悪意を持った場合にできること
#### 外から
- Nginx & OAuth/SSO のバグをついて中に入る

#### Nginx 経由で SlowDash へのアクセスだけができる場合
- SlowDash のバグをついて権限奪取
- スクリプトの編集ができるなら SlowMesh にニセの自己申告（超簡単；スクリプト編集権限が必要）
  - 任意 SlowDash タスクの実行
  - （そもそもスクリプト編集ができる段階で任意 OS コマンドの実行が可能）
- Nginx で WebSocket が通れるなら（遮断が通常運用の想定），外部の SlowTask が嘘の自己申告
  - 任意 SlowDash タスクの実行

#### ネットワークに入れる場合
- （そもそも SlowDash を経由しなくてもデバイスを直接操作できるし，データーベースも触れる）

#### SlowDash PC にログインできる場合
- X-Remote-User を偽装して権限奪取（簡単）
  - WebMesh 経由で SlowMesh への publish で任意 SlowDash タスク実行
  - Web 経由のスクリプト編集を許している場合は slowdash アカウントでの任意 OS コマンド実行
- （そもそもログインしているので任意 OS コマンドを実行できる）

#### SlowDash の管理アカウントにログインできる場合
- 設定変更で悪いスクリプトを忍び込ませる
- （そもそも SlowDash 管理権限で任意コマンドを実行できる）

#### 本番用 SlowDash のソースコードを編集できる場合
- SlowDash ログに痕跡を残さず悪いことをする


### 対策
#### SlowDash コードを編集できる場合
- 何もできない
- 締め出すかあきらめるしかない

#### SlowDash 設定ファイルを編集できる場合
- 編集記録の自動保存くらい? (Git 自動コミットと実行時確認?)
- プロジェクト全体のチェックサムとリモート保存の「承認済み」リストとの比較？
- 締め出すかあきらめるのが現実的

#### SlowDash PC に他アカウントでログインできる場合
- ないよりマシ隔離：VPN の中なら SlowDash 内蔵の HTTPS + 基本認証を使う
  - uvicorn の HTTPS を使っている．それなりに安全だと思う(VPN の中には「最強レベル攻撃者」がいない想定)
- 簡易隔離：SlowDash + Nginx 全体を Docker Compose に入れる ＋ 外部 OAuth2/SSO 認証
  - 設定ファイルは編集できない前提（OS レベルのファイルアクセス管理）
- 隔離：仮想環境を作ってその中で SlowDash を使う
- (それでもデバイスは直接アクセスできる)

#### 本格隔離（現実的な第一候補）
- 測定系サブネットを分離してファイアウォールを入れる
- 権限奪取を止める（SlowTask の user 自己申告を変更できなくする）
  - SlowDash にバグがないなら：
    - スクリプト編集機能を SlowdashProject.yaml で無効にする（デフォルト）
    - プロキシで WebSocket を通さないようにして，外部からの SlowMesh アクセス（外部の SlowTask からのアクセス）を止める（例ではそうなっている）
  - 完全にするなら:
    - SlowDash (Nginx) を外に見せない．サブネット内部へのアクセスは ssh のみ
    - 隔離 SlowDash の外(DMZ)に別の SlowDash を走らせて，隔離 SlowDash から DMZ SlowDash にモニタデータだけを HTTP POST する
    - データベースも（必要なデータだけ）別にコピーしておく
    - 外部から操作が必要なら自分で ssh トンネルを掘る


## その他
- 何をしても，正当ユーザーアカウントの乗っ取りは常にありえる．バックアップとインターロックはセキュリティとは別の話．
- 内部の人が悪意のあるWebコンテンツを作成すれば，XSS により他のユーザー権限での実行ができる．心の隅で覚えておく．
