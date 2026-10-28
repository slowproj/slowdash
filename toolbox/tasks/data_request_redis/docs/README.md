# Task: On-Demand Data Requests via Redis

Requests data from external analysis programs via Redis only for the channels currently displayed in SlowDash browsers, and streams the returned data to the browsers in real time.

| Property | Description |
|---|---|
| Name | `data_request_redis` |
| Input Topics | `sd.web.data.subscription.>` |
| Output Topics | `data.stream.{channel}` |
| Export Functions | - |
| Config Contents | - |
| External Dependencies | Redis server |

Maintainer: Sanshiro Enomoto


## Description
This task is useful for an online monitor with so many channels that streaming all of them in real time is impractical. Rather than streaming all channels, this task tells user analysis programs running outside the SlowDash mesh which channels are currently displayed in the SlowDash browsers, so that they write only those channels' data. For example, the example analysis program creates 128 histograms internally, but writes only the few histograms being shown in the browsers to the Redis Key-Value Store (KVS).

The task works in two directions:

- **Request**: When the task detects a change in the browser configurations (through the WebMesh notification on the `sd.web.data.subscription.>` topic), it fetches the list of data channels attached to the browsers from the SlowDash server (the "public configuration" `webmesh.attached`). It then publishes the list to the Redis PubSub topic `slowdash:request:data`, to which the analysis programs subscribe. The message is a comma-separated string of channel names (e.g., `hist034,hist051`), and is an empty string when no channel is requested. Each message contains the complete list of currently requested channels, not a difference from the previous one, because the list can also shrink, for example when a browser is closed. The analysis programs should therefore replace their previous list with the new one, and stop writing the channels that are no longer in the list.
- **Data**: The task monitors the Redis KVS for data written by the analysis programs. When new data is written, it streams the values to `data.stream.{channel}` so that the browsers can display them immediately. Since the data written to the KVS are streamed, the browsers receive the same data both through streaming and through the data store. The contents are identical, so this does not affect the display.

Regular Slow Task scripts on Slow Mesh do not need to use this task for this purpose. They can do what this task does (fetching `webmesh.attached` from the server's public configuration when a `sd.web.data.subscription.>` message arrives) directly in the script.


## Usage

### Setup
This task assumes that Redis is used for the communication between SlowDash and the analysis programs.
If no Redis server is running, install Redis.

If you need a temporary Redis server to run the example, the Docker Compose setup in `utils/testbench` of SlowDash is convenient:
```
cd PATH/TO/SLOWDASH/utils/testbench
docker compose up -d redis
```
When you are done, `docker compose down` removes everything and leaves a clean state.

### Project file example
```yaml
slowdash_project:
  title: Redis Data Request

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

### Parameters

| Name | Default | Description | Example |
|---|---|---|---|
| `redis_url` | - | URL for the Redis system, including the DB number | `redis://localhost:6379/12` |


## Example
### Overview
The `dqm.py` script in the `examples` directory is a dummy user analysis program.
It generates dummy data from Poisson random numbers and creates 128 histograms internally, named like `hist034`.

Only the histograms of the requested channels are written to the Redis KVS during operation. At startup, however, the script writes all the empty histograms to the KVS, so that SlowDash can build the full list of available channels from the KVS entries.

The analysis script receives data request notifications from the SlowDash task through Redis PubSub and updates its internal `requested_channels` list:

```python
redis_url = 'redis://localhost/12'
data_request_topic = 'slowdash:request:data'

requested_channels = []

def receive_data_request(message):
    global requested_channels
    requested_channels = message.get('data', '').split(',')
    print(f'Requested Channels: {requested_channels}')

import redis
redis_client = redis.from_url(redis_url, decode_responses=True)

pubsub = redis_client.pubsub()
pubsub.subscribe(**{data_request_topic: receive_data_request})
pubsub.run_in_thread(sleep_time=0.1, daemon=True)

# ... user analysis loop ...
# Write data to Redis only for the channels in `requested_channels`.
```

For demonstration purposes, the histograms are cleared periodically, so that the growth of the displayed histograms can be seen.

To keep the demonstration simple, this example reads the data, fills the histograms, and writes the histogram data to Redis all in the same loop. In a real application, however, the histograms should be written to Redis at a constant time interval, independent of the data rate.

### Running the example
This example uses Redis DB number `12`.
If this conflicts with your setup, change it in `dqm.py` and `SlowdashProject.yaml`.

To run the example, first make sure the Redis server is running, then run the `dqm.py` script.
Since `dqm.py` uses the SlowPy library to create histograms, activate the SlowPy venv before running it:

```
cd examples
slowdash-activate-venv
python dqm.py
```

Then start the SlowDash server and connect a browser to it:

```console
slowdash --port=18881
```

When you select a channel from the Channel List in the browser, a new panel opens to display its data. This starts the chain of notifications that ends at the `dqm.py` analysis script.
