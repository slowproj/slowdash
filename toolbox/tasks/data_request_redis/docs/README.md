# Redis Data Request

## Specifications

|---|---|
| Name | 'data_request_redis' |
| Input Topic | `sd.web.data.subscription.>` |
| Output Topic | `data.stream.{channel}` |
| Export Functions | none |
| Config Contents | none |


## Description
This task notifies user analysis programs running outside the SlowDash mesh with the channels being displayed by the SlowDash browsers though Redis PubSub. This also monitors the Redis Key-Value Store (KVS) for data being written to it by the analysis programs, and when new data is written, it streams the data values to `data.stream.{channel}` for immediate display on the browsers.

This is useful for an online monitor with a large number of channels, too many channels to stream in real-time. The analysis program in the example creates 128 histograms internally, but only a few histograms that are being shown in the browsers are sent to the Redis KVS.

When the task detects changes on browser configurations (through WebMesh's notification on the `sd.web.data.subscription.>` topic), it fetches the list of connected data channels from the SlowDash server ("public configuration" of `webmesh.attached`), and publishes the list to the Redis Pubsub with a topic of `slowdash:request:data`.


## Usage

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

| Name | Default | Description |
|---|---|---|
| `redis_url` | - | URL for the Redis system, including the DB number |


## Example
The `dqm.py` script in the `examples` directory is the dummy user analysis program.
It uses Poisson random numbers for dummy data, and creates 128 histograms internally, named like `hist034`.

The analysis scripts receives data request notifications from the SlowDash task through Redis PubSub and updates its internal `requested_channel` list:

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
pubsub.subscribe(**{data_request_topic:receive_data_request})
pubsub.run_in_thread(sleep_time=0.1, daemon=True)
```

This example uses Redis DB number `12`.
If this causes a problem, change it by editing the `dqm.py` and `SlowdashProject.yaml` files.

To run the example, first make the Resis server ready, then run the `dqm.py` script.
Since the example `dqm.py` script uses the SlowPy library to create histograms, activate the SlowPy venv before running it.

```console
$ cd examples
$ slowdash-activate-venv
$ python dqm.py
```

Then start SlowDash server and connect the browser to it:

```console
$ slowdash --port=18881
```

From the Channel List, if you choose a channel, a new panel to display the channel data will open, which will then start the chain of notifications to the `dqp.py` analysis script.
