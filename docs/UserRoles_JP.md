# 認証権限管理

## Scope
Role による権限管理(Authorization)は意図しない誤操作を防ぐためのもの．
認証(Authentication)を通った場合には全ての操作ができると想定する．

## 認証
- まずは Slowlette 組み込みの基本認証（＋プロキシによる HTTPS）で user を取得
- 本番ではプロキシから取得できるように（セキュリティ周りを自作しない方針）
  - Nginx 経由で外部認証に接続できる（OAuth2, SSO, etc.）
  - 特定端末向けクライアント証明書もできる (mTLS)
  - ユーザー名は X-Remote-User ヘッダで取得（クライアントの偽装に注意）
- 認証を有効にしていない場合の user は `nobody`

## 権限
- user_name への user_role の割当は Slowdash 設定ファイル
  - user_name / user_role に特殊文字は受け入れない
  - user_name にも  role にも階層構造はなし
  - user_role は先頭に `@` をつけて user_name と合わせ，user にする．
    - 例： operator と admin の role を持った sanshiro は user: [ 'sanshiro', '@operator', '@admin' ]
  - 将来拡張: role に包含構造をもたせられる．user 構築時点で展開しておく
    - 例： `"roles": [ { 'name': 'operator', 'includes': [ 'analyzer' ] ]`
  - 許可は `allowed is None or set(user) & set(allowed)` 演算．「安全のための禁止を追加する」方針
- Slowlette ミドルウェアで slowlette.Request に user を追加
  - 全てのウェブリクエストで user 情報が使える
- api/config のリプライにユーザー情報を含めてブラウザにも通知
  - ブラウザ側も user_name / user_role がわかる（偽装可）

## 利用
### サーバー側
- ユーザーレイアウト（slowdash/slowplot）では，それぞれの見せる・見せないを role で選択（表示のみ・直接取得は可能）
- スタートページも２種類用意？
- コマンド実行では，role を確認（強制）
- タスクコントロールは SlowdashProject.yaml で個別に実行権限を指定（強制）
- スクリプト編集権限は？
  - 登録タスクに関しては SlowdashProject.yaml で指定できる
  - 自由作成スクリプトはあまり制限したくない（解析目的もある）
    - まずは一律の「作成許可」ロール（一律禁止，一律許可は利用者次第）
    - 将来的には:
      - Mesh への publish を許さない（LocalMesh に接続）にすれば，間違えてコマンドを送ることはない
        - [ 'data.>' および  'alarm.>' ] への publish だけを許可とかもできるかも
      - 解析サンドボックスを作成することも検討
- ユーザー名は操作ログにも入る

### ブラウザ側
- どこかにユーザー名・ロール名を表示
- できるのは表示管理のみ．ブラウザはその気になればどんなコマンドでもサーバーに送れる．操作許可はサーバー側．
- Canvas パネルではページ単位で操作許可，さらに個別デバイスでオーバーライド可能
- HTML パネルは何もしない（HTMLを含むレイアウト自体を表示するかどうかでコントロール）

### Task 側
- SlowMesh のヘッダに user 情報を付加（認証を通った後なら偽装可，一部は自己申告）
- Task 内一律なら SlowdashProject.yaml から許可設定
- ハンドラごとなら `@mesh.on('control.HV.>', allowed='@operator')`
- 拒否に例外を投げれば SlowMesh がエラーレスポンスを返す
  