import logging, json

import slowpy
tasklet = slowpy.mesh.Tasklet()

import redis
redis_client, redis_pubsub = None, None

subscription_channels = []


@tasklet.initialize()
async def initialize(params):
    global redis_client, redis_pubsub

    redis_url = params.get('redis_url', 'redis://localhost/2')
    try:
        redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=60,
        )
        redis_client.ping()
    except Exception as e:
        logging.error(f'Redis: unable to connect to Redis server: {redis_url}: {e}')
        try:
            redis_client.close()
        except:
            pass
        redis_client = None
        return

    logging.info(f'Redis connected: {redis_url}')

    redis_client.config_set('notify-keyspace-events', 'E$')
    redis_pubsub = redis_client.pubsub()
    redis_pubsub.subscribe('__keyevent@12__:set')


@tasklet.loop(interval=0.1)
async def watch_redis_set():
    if redis_pubsub is not None:
        message = redis_pubsub.get_message(timeout=0.01)
        if message:
            ch = message.get('data')
            if ch in subscription_channels:
                data = redis_client.get(ch)
                try:
                    value = json.loads(data)
                except:
                    value = data
                await tasklet.mesh.aio_publish(slowpy.mesh.DataPacket(value,tag=ch).to('data.stream'))
    
    
@tasklet.finalize()
async def finalize():
    global redis_client, redis_pubsub
    if redis_pubsub is not None:
        redis_pubsub.close()
        redis_pubsub = None
    if redis_client is not None:
        redis_client.close()
        redis_client = None
        

        
# This function is called when a browser creates a new plot.
@tasklet.mesh.on('sd.web.data.subscription.>')
async def on_subscription(headers, body):
    global subscription_channels
    subscription_channels.clear()

    # Get the list of the streaming-data subscribers from the SlowDash server config.
    # The list is in the WebMesh public config at "webmesh/attached".
    config = await tasklet.dash.aio_get_config()
    for topic, client in config.get('webmesh', {}).get('attached', {}).items():
        if topic.startswith('data.*.'):
            ch = topic[len('data.*.'):]
            if len(ch) > 0 and ch[0] != '@':
                subscription_channels.append(ch)
                
    if redis_client is not None:
        redis_client.publish('slowdash:request:data', ','.join(subscription_channels))
