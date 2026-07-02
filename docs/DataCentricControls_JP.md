---
title: Data Centric Controls and Monitor
---


# 概要
SlowMesh/SlowTask においては，RPC ではなく，PubSub メッセージによるコントロールを提案しています．
これは，「望む状態を指定」することにより，システムを構成する各タスクがそれを実現するように協調して動作することを期待します．コントロールを出す側は，具体的に「誰が」「何を」やるかは指定しません．
これは，従来のように，RPCなどを使用して，相手を指定してコマンドを送る方法と大きく異なります．
基本的に，「自分の望むことだけをやって」「周りに誰がいて何をするかは考えず」「誰かが望みをかなえてくれると期待する」のが SlowDash のやり方です．
これにより各タスクの独立性（自分の望むことだけをする・知らせる）と粗結合（知らない誰かが何とかしてくれると期待）を実現しています．

RPC によるコントロールと異なり，PubSub メッセージによるコントロールでは，戻り値が存在しないため，コマンドの成功またはエラーを直接取得することができません．
コントロールが成功したかどうかは，モニタタスクが，システムが望む状態に移行したかどうかを監視することにより行います．

典型的には，コントロールを出すタスクがコントロールを Publish し，モニタがそれを傍受したら，そのことを発出タスクに通知し，それ以降の責任はモニタが引き受けます．
コントロールメッセージには，直接の操作対象に加え，その結果として期待するシステム状態も記述されます．
この仕組みにより，モニタが期待するシステム状態が変化する状況においても，データ監視条件をコントロールに応じて変化させることができます．

一度モニタが始動すると，状態を示すデータは継続的にモニタされるようになります．
このモニタ間隔は，最初の一点を除き，データ生成側が提示します．
通常，データの読み出し間隔は，データ生成元が知っているはずなので，このようにすることによりモニタ側に事前にデータ間隔を伝える必要がなくなります．
最初の一点までの時間は，コントロール側が指定します．


# 実装
## コントロールメッセージ
### トピック: `control.{target}`
```json
{
    "target": target,
    "value": value,
    
    "effective_at": timestamp,
    "deadline": timestamp,
    
    "consequences": [
        {
            "topic": data_topic, 
            "condition": {
                "range": [low, high]
            },
            "delay": max_time_to_data
        }
        ....
    ],
    
    "issued_by": mesh_id,
    "timestamp": timestamp
}
```

- `effective_at` でコマンドを実行する時間を指定．指定がなければ即実行
- `deadline` までにコマンド実行を完了できなければエラー

- `consequences` はモニタに使われる．もちろん．コントロール実行側がエラーやアラームを出しても良い．
- `consequences/condition` におけるデータチェックは，
  - ` `: 空；データがあれば内容は問わない
  - `"range": [ low,high ]`: レンジチェック
  - `"value": value` / `"values": [ values ]`: 整数または文字列に対する一致チェック
  - `"match": pattern`： 文字列値に対する正規表現チェック
  - `"bits": mask` / `"zero_bits": mask`: 整数値に対するビットチェック
  - `"custom": { "type": {name}, "params": {...}` }: カスタムチェック
  - その他，モニタシステムで使われる Data Condition が使える

- `consequences/condition` に指定できるその他のパラメータ
  - `severity`: grace を超えて条件が満たされない場合の severity レベル．デフォルト `error`
  - `grace`: 条件が満たされない場合の最大連続許容回数．デフォルト `0`

- `delay` を超えてデータが来ない場合はエラーとなる．指定されてなければずっと待つ．

- 同じ `topic` に対する複数の consequence がある場合は，後から到着したものが上書きをする．
- `consequence` に `name` が指定されている場合，`{name}.{topic}` に対して上書きする．


## データ形式
### トピック: `data.{category}.{channel}`
- `category` は，データ生成側が，データがどのように使われるかの期待を示す．
  - `monitor`: 主に実時間モニタを目的とした高頻度データ
  - `store`: 永続記録装置に記録することを期待した必要データ
  
```json
{
    "channel": channel,
    "timestamp": timestamp,
    "value": value,
    
    "next_delivery": max_time_to_next_data
}
```

- コントロールメッセージの `consequences` と同じデータモニタが適用される
- モニタは，`next_delivery` を超えてデータが来ない場合はエラーとする
- `next_delivery` が存在しない場合は，モニタはタイムアウトチェックをしない
- `next_delivery` に `None`/`null` または非正値を指定すると，このトピックに対するモニタが停止する


## モニタ
モニタタスクが `control.>` と `data.>` を subscribe し，状態をチェック．
期待どおりの状態・状態遷移が起きない場合はアラームを出す．

- モニタがコントロールメッセージを傍受したら，発行元に Acknowledged を送る．
  - これにより，送り出し側は，結果がモニタされたことを確認して安心できる．
  - Acknowledge が来なかったら，メッシュが不通かモニタが死んでいるということ．
- モニタはアラーム状態を時系列データとして送り出す．
  - `monitor.{category}.{channel}`
  - Alarm タスクがこれを見てアラーム処理をする
  - Store タスクがこれを記録しても良い．過去のデータに対するアラーム状態を取得できる．


### トピック: `acknowledge.{mesh_id}`
```json
{
    "message_id": message_id,
    "issued_by": self.mesh_id,
    "timestamp": timestamp
}
```
- `message_id` は，コントロール送出タスクの Message ID．ヘッダから取得する．

### トピック: `monitor.{category}.{channel}`
- `category` は，`data` トピックと同じ

```json
{
    "channel": channel,
    "timestamp": timestamp,
    "severity": severity,
    "message": message
}
```




