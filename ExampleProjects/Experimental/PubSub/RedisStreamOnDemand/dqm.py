

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



import slowpy

channels = [ f'hist{ch:02}' for ch in range(128) ]
histograms = { ch: slowpy.Histogram(20, 0, 20) for ch in channels }

# initial filling of all the channals so that SlowDash recognize the channels
for ch, hist in histograms.items():
    redis_client.set(ch, str(hist))

    
import time
import numpy as np

while True:
    do_clear = int(time.time()) % 100 == 0
    
    for ch, hist in histograms.items():
        if do_clear:
            hist.clear()
            
        data = np.random.poisson(5)
        hist.fill(data)
        
        if ch in requested_channels:
            redis_client.set(ch, str(hist))

    time.sleep(0.2)
