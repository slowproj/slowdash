# Created by Sanshiro Enomoto on 22 May 2024 #
# Updated by Sanshiro Enomoto on 16 March 2026 for async #

import asyncio, time
import slowpy.control as spc

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class RedisNode(spc.ControlNode):
    def __init__(self, url, **kwargs):
        self.url = url
        self.kwargs = { k:v for k,v in kwargs.items() }
        
        self.redis = None
        self.pubsub_list = []

        self.open_lock = asyncio.Lock()

        
    def __del__(self):
        pass

    
    async def aio_open(self, retries=12, retry_interval=5, force_check=False):
        async with self.open_lock:
            return await self._aio_open(retries=retries, retry_interval=retry_interval, force_check=force_check)

    async def _aio_open(self, retries, retry_interval, force_check):
        if self.redis is not None:
            if not force_check:
                return True
            try:
                await self.redis.ping()
            except Exception as e:
                logging.error(f'AsyncRedis: Redis connection found dead; restarting...')
                await self.redis.aclose()
                self.redis = None
            else:
                return True
        
        try:
            import redis.asyncio as redis
        except Exception as e:
            logging.error(f'AsyncRedis: {e}')
            return False
        
        for i in range(retries):
            try:
                self.redis = redis.from_url(self.url, decode_responses=True, health_check_interval=60, **self.kwargs)
                await self.redis.ping()
                break
            except Exception as e:
                logging.info(f'Redis not connected: {url}: retry in {retry_interval} sec')
                asyncio.sleep(retry_interval)
        else:
            logging.info(f'Redis not connected: {url}: retry in {retry_interval} sec')
            self.redis = None
        
        if self.redis is None:
            logging.error(f'Redis not loaded: {url}')

        return self.redis is not None

        
    async def aio_close(self):
        for pubsub in self.pubsub_list:
            await pubsub.aclose()
        if self.redis is not None:
            await self.redis.aclose()

    
    async def aio_set(self, value):
        pass

    
    async def aio_get(self):
        if not await self.aio_open():
            return None
        return await self.redis.info()

    
    ## Redis specific functions ##
    async def aio_get_info(self):
        if not await self.aio_open():
            return None
        return await self.redis.info()

    
    async def aio_get_keys(self, pattern='*'):
        if not await self.aio_open():
            return None
        return await self.redis.keys(pattern)

    
    ## child nodes ##
    def string(self, name):
        return RedisStringNode(self, name)

    
    def hash(self, name):
        return RedisHashNode(self, name)

    
    def json(self, name, base='$'):
        return RedisJsonNode(self, name, base)

    
    def ts(self, name, length=3600, to=0):
        return RedisTimeseriesNode(self, name, length, to)


    def publish(self, topic):
        return RedisPublishNode(self, topic)

    
    def subscribe(self, topic_pattern):
        return RedisSubscribeNode(self, topic_pattern)

    
    @classmethod
    def _node_creator_method(cls):
        def async_redis(self, url):
            if True:  # create a new connection everytime (othwerwise task stop/start will use the same connection)
                return RedisNode(url)
            
            try:
                keys = [ key for key in self._redis_nodes.keys() ]
            except:
                self._redis_nodes = {}
                keys = []
            if url is None:
                if len(keys) == 0:
                    raise spc.ControlException('Redis URL not provided')
                else:
                    url = keys[-1]
            node = self._redis_nodes.get(url, None)
                
            if node is None:
                node = RedisNode(url)
                self._redis_nodes[url] = node

            return node

        return async_redis

    

class RedisStringNode(spc.ControlNode):
    def __init__(self, redis_node, name):
        self.redis_node = redis_node
        self.name = name
            
    async def aio_set(self, value):
        if not await self.redis_node.aio_open():
            return None
        await self.redis_node.redis.set(self.name, value)
    
    async def aio_get(self):
        if not await self.redis_node.aio_open():
            return None
        return await self.redis_node.redis.get(self.name)

    async def aio_do_incr(self, amount=1):
        if not await self.redis_node.aio_open():
            return None
        return await self.redis_node.redis.incr(self.name, amount)
    

    
class RedisHashNode(spc.ControlNode):
    def __init__(self, redis_node, name):
        self.redis_node = redis_node
        self.name = name
            
    async def aio_set(self, value):
        if not await self.redis_node.aio_open():
            return None
        if type(value) == dict:
            await self.redis_node.redis.hset(self.name, mapping=value)
            
    async def aio_get(self):
        if not await self.redis_node.aio_open():
            return None
        return await self.redis_node.redis.hgetall(self.name)
    
    # child nodes #
    def field(self, fieldname):
        return RedisHashFieldNode(self.redis_node, self.name, fieldname)

    
    
class RedisHashFieldNode(spc.ControlNode):
    def __init__(self, redis_node, name, fieldname):
        self.redis_node = redis_node
        self.name = name
        self.fieldname = fieldname
        
    async def aio_set(self, value):
        if not await self.redis_node.aio_open():
            return None
        await self.redis_node.redis.hset(self.name, self.fieldname, value)

    async def aio_get(self):
        if not await self.redis_node.aio_open():
            return None
        return await self.redis_node.redis.hget(self.name, self.fieldname)

    
    
class RedisJsonNode(spc.ControlNode):
    def __init__(self, redis_node, name, base='$'):
        self.redis_node = redis_node
        self.name = name
        self.base = base
    
    async def aio_set(self, value):
        if not await self.redis_node.aio_open():
            return None
        await self.redis_node.redis.json().set(self.name, self.base, value)

    async def aio_get(self):
        if not await self.redis_node.aio_open():
            return None
        result = await self.redis_node.redis.json().get(self.name, self.base)
        if type(result) is list:
            if len(result) == 0:
                return None
            elif len(result) == 1:
                return result[0]
        return result

    ## child nodes ##
    # redis().json(name).node(name)
    def node(self, name):
        return RedisJsonNode(self.redis_node, self.name, self.base + '.' + name)

    
    
class RedisTimeseriesNode(spc.ControlNode):
    def __init__(self, redis_node, name, length=3600, to=0):
        self.redis_node = redis_node
        self.name = name
        self.length = length
        self.to = to    # zero for "now", positive for UNIX timestamp, negative for time to "now"
    
    async def aio_set(self, value):
        if not await self.redis_node.aio_open():
            return None
        for t,x in value:
            await self.redis_node.redis.ts().add(self.name, t, x)

    async def aio_get(self):
        if not await self.redis_node.aio_open():
            return None
        to = self.to if self.to > 0 else time.time() + self.to
        start = to - self.length
        return await self.redis_node.redis.ts().range(self.name, int(1000*start), int(1000*to))
       
    ## child nodes ##
    # Redis.ts(name).current() to aio_set()
    def current(self):  
        return RedisTimeseriesCurrentNode(self)

    # Redis.ts(name).last() to aio_get()
    def last(self):
        return RedisTimeseriesLastNode(self)

    
    
class RedisTimeseriesCurrentNode(spc.ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    async def aio_set(self, value):
        await self.parent.aio_set([(int(1000*time.time()), value)])

    async def aio_get(self):
        return None
        
    
    
class RedisTimeseriesLastNode(spc.ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    async def aio_set(self, value):
        pass

    async def aio_get(self):
        if self.parent.to == 0:
            return await self.parent.redis_node.redis.ts().get(self.parent.name)
        else:
            to = self.parent.to if self.parent.to > 0 else time.time() + self.parent.to
            start = to - self.parent.length
            ts = await self.parent.redis_node.redis.ts().revrange(self.parent.name, int(1000*start), int(1000*to), count=1)
            if len(ts) > 0:
                return ts[0]
            else:
                return (None, None)
        
    ## child nodes ##
    # Redis.ts(name).last().value()
    def value(self):
        return RedisTimeseriesLastValueNode(self)

    # Redis.ts(name).last().time()
    def time(self):
        return RedisTimeseriesLastTimeNode(self)

    # Redis.ts(name).last().lapse()    
    def lapse(self):
        return RedisTimeseriesLastLapseNode(self)

    
    
class RedisTimeseriesLastValueNode(spc.ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    async def aio_set(self, value):
        pass

    async def aio_get(self):
        return (await self.parent.aio_get())[1]


    
class RedisTimeseriesLastTimeNode(spc.ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    async def aio_set(self, value):
        pass

    async def aio_get(self):
        return (await self.parent.aio_get())[0]/1000.0


    
class RedisTimeseriesLastLapseNode(spc.ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    async def aio_set(self, value):
        pass

    async def aio_get(self):
        return time.time() - (await self.parent.aio_get())[0]/1000.0


    
class RedisPublishNode(spc.ControlNode):
    def __init__(self, redis_node, topic):
        self.redis_node = redis_node
        self.topic = topic


    async def aio_set(self, value):
        if not await self.redis_node.aio_open():
            return None
        await self.redis_node.redis.publish(self.topic, value)


        
class RedisSubscribeNode(spc.ControlNode):
    def __init__(self, redis_node, topic_pattern, timeout=None):
        self.redis_node = redis_node
        self.topic_pattern = topic_pattern
        self.timeout = timeout
        
        self.pubsub = None
        
        
    async def aio_get(self):
        if not await self.redis_node.aio_open():
            return None
        if self.pubsub is None:
            self.pubsub = self.redis_node.redis.pubsub()
            self.redis_node.pubsub_list.append(self.pubsub)
            await self.pubsub.psubscribe(self.topic_pattern)
            
        if self.timeout is None or self.timeout < 0:
            return await self.pubsub.get_message(ignore_subscribe_messages=True)
        else:
            return await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=self.timeout)


    ## child nodes ##
    # Redis.subscribe(topic_pettern).data()
    def data(self):
        return RedisSubscribeDataNode(self)
        

    
class RedisSubscribeDataNode(spc.ControlNode):
    def __init__(self, subscribe_node):
        self.subscribe_node = subscribe_node
        

    async def aio_get(self):
        while True:
            msg = await self.subscribe_node.aio_get()
            if msg is None:
                return None
            if msg.get('type', None) == 'pmessage':
                return msg.get('data', None) if msg is not None else None
