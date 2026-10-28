---
title: Toolbox
---

# 概要
Slow Task および User Module の Python スクリプトは，Toolbox に入れることにより，共有部品として使用可能になります．
SlowDash パッケージには，すでにいくつかの汎用の Slow Task スクリプトが含まれています．

Toolbox にあるスクリプトを使用するには，`SlowdashProject.yaml` の `task` エントリで，タスク名の前に `@toolbox/` を付加します．
その他は，プロジェクトディレクトリの `config` にあるスクリプトと同様の振る舞いになります．

以下は，Toolbox にある `data_request_redis` という Slow Task を使用する例です．

```yaml
slowdash_project:
  title: Redis Streaming-on-Demand

  environment:
    - REDIS_URL=redis://localhost:6379/12

  task:
    - name: "@toolbox/data_request_redis"
      auto_load: true
      parameters:
        redis_url: ${REDIS_URL}

  data_source:
    url: ${REDIS_URL}
```

SlowTask の実体は，`toolbox/tasks/data_request_redis/slowtask-data_request_redis.py` というファイルです．
Toolbox の Task ディレクトリには，Python スクリプトの他に，それぞれのタスク専用のドキュメント (`docs`) および使用例 (`examples`) があります．
