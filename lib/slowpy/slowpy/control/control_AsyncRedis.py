# Created by Sanshiro Enomoto on 22 May 2024 #
# Updated by Sanshiro Enomoto on 16 March 2026 for async #

import asyncio, time, json
from slowpy.control import ControlNode, ControlException

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RedisNode(ControlNode):
    def __init__(self, url, **kwargs):
        self.url = url
        self.kwargs = { k:v for k,v in kwargs.items() }

        self.decode_response = self.kwargs.get('decode_response', True)
        
        self.redis = None
        self.subscriber_list = []

        self.open_lock = asyncio.Lock()
        self.retry_wait = 10
        self.last_connect_attempt_time = 0

        
    def __del__(self):
        pass

    
    async def aio_open(self):
        async with self.open_lock:
            if self.redis is not None:
                return True

            now = time.monotonic()
            if now - self.last_connect_attempt_time < self.retry_wait:
                return False
            self.last_connect_attempt_time = now
            
            try:
                import redis.asyncio as redis
            except Exception as e:
                logger.warning('Redis: radis python module import error: %s' % str(e))
                return False
        
            try:
                self.redis = redis.from_url(
                    self.url,
                    decode_responses=self.decode_response,
                    health_check_interval=60,
                    retry_on_timeout = True, socket_connect_timeout = 10,
                    **self.kwargs
                )
                await self.redis.ping()
            except:
                logger.warning(f'AsyncRedis: unable to connected to Redis server: {self.url}')
                self.redis = None
            else:
                logger.info(f'AsyncRedis: connected: {self.url}')

        return self.redis is not None

        
    async def aio_close(self):
        for sub in self.subscriber_list:
            try:
                await sub.pubsub.aclose()
            except:
                pass
        if self.redis is not None:
            try:
                await self.redis.aclose()
            except:
                pass
            finally:
                self.redis = None


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


    def publisher(self, topic):
        return RedisPublisherNode(self, topic)

    
    def subscriber(self, topic_pattern, timeout=None):
        return RedisSubscriberNode(self, topic_pattern, timeout=timeout)

    
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
                    raise ControlException('Redis URL not provided')
                else:
                    url = keys[-1]
            node = self._redis_nodes.get(url, None)
                
            if node is None:
                node = RedisNode(url)
                self._redis_nodes[url] = node

            return node

        return async_redis

    

class RedisStringNode(ControlNode):
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
    

    
class RedisHashNode(ControlNode):
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

    
    
class RedisHashFieldNode(ControlNode):
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

    
    
class RedisJsonNode(ControlNode):
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

    
    
class RedisTimeseriesNode(ControlNode):
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
    # redis().ts(name).current() to aio_set()
    def current(self):  
        return RedisTimeseriesCurrentNode(self)

    # redis().ts(name).last() to aio_get()
    def last(self):
        return RedisTimeseriesLastNode(self)

    
    
class RedisTimeseriesCurrentNode(ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    async def aio_set(self, value):
        await self.parent.aio_set([(int(1000*time.time()), value)])

    async def aio_get(self):
        return None
        
    
    
class RedisTimeseriesLastNode(ControlNode):
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
    # redis().ts(name).last().value()
    def value(self):
        return RedisTimeseriesLastValueNode(self)

    # redis().ts(name).last().time()
    def time(self):
        return RedisTimeseriesLastTimeNode(self)

    # redis().ts(name).last().lapse()    
    def lapse(self):
        return RedisTimeseriesLastLapseNode(self)

    
    
class RedisTimeseriesLastValueNode(ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    async def aio_set(self, value):
        pass

    async def aio_get(self):
        last = await self.parent.aio_get()
        if last is None:
            return None
        return last[1]


    
class RedisTimeseriesLastTimeNode(ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    async def aio_set(self, value):
        pass

    async def aio_get(self):
        last = await self.parent.aio_get()
        if last is None:
            return None
        return last[0]/1000.0


    
class RedisTimeseriesLastLapseNode(ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    async def aio_set(self, value):
        pass

    async def aio_get(self):
        last = await self.parent.aio_get()
        if last is None:
            return None
        return time.time() - last[0]/1000.0


    
class RedisPublisherNode(ControlNode):
    def __init__(self, redis_node, topic):
        self.redis_node = redis_node
        self.topic = topic


    async def aio_set(self, value):
        if not await self.redis_node.aio_open():
            return None
        try:
            await self.redis_node.redis.publish(self.topic, value)
        except Exception as e:
            logger.warning(f'AsyncRedis: redis.publish(): {e}')

            
    ## child nodes ##
    # redis().publisher(topic).json(headers=None).set(value)
    def json(self):
        return RedisPublisherJsonNode(self)
    
            
        
class RedisSubscriberNode(ControlNode):
    def __init__(self, redis_node, topic_pattern, timeout=None):
        self.redis_node = redis_node
        self.topic_pattern = topic_pattern
        self.timeout = timeout
        
        self.pubsub = None
        self.disconnected = False
        
        
    async def aio_get(self):
        if not await self.redis_node.aio_open():
            await asyncio.sleep(1)
            return None
        
        if self.pubsub is None:
            self.pubsub = self.redis_node.redis.pubsub()
            self.redis_node.subscriber_list.append(self)
            try:
                await self.pubsub.psubscribe(self.topic_pattern)
            except Exception as e:
                logger.warning(f'AsyncRedis: redis.psubscribe(): {e}')
                return None

        try:
            await self.pubsub.connect()  # check connection, if disconnected, re-connect and re-subscribe
            if self.disconnected:
                self.disconnected = False
                logger.info(f'AsyncRedis: reconnected')
            if self.timeout is None or self.timeout < 0:
                return await self.pubsub.get_message(ignore_subscribe_messages=True)
            else:
                return await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=self.timeout)
        except Exception as e:
            await asyncio.sleep(1)
            if not self.disconnected:
                self.disconnected = True
                logger.warning(f'AsyncRedis: redis.pubsub.get_message(): {e}')


    ## child nodes ##
    # redis().subscriber(topic_pettern).json()
    def json(self, headers=None):
        return RedisSubscriberJsonNode(self)
        

    
class RedisPublisherJsonNode(ControlNode):
    def __init__(self, publisher_node, headers=None):
        self.publisher_node = publisher_node
        self.headers = dict(headers or {})
        

    async def aio_set(self, value):
        try:
            doc = json.dumps(value)
        except Exception as e:
            logger.warning('AsyncRedis: publisher(): unable to convert to JSON: {e}')
            return None
        
        return await self.publisher_node.aio_set(doc)



class RedisSubscriberJsonNode(ControlNode):
    def __init__(self, subscriber_node):
        self.subscriber_node = subscriber_node
        

    async def aio_get(self):
        while True:
            message = await self.subscriber_node.aio_get()
            if message is None:
                return None, None
            
            if message.get('type', None) == 'pmessage':
                headers = {
                    'topic': message.get('channel', None),
                }
                body = message.get('data', None)
                if type(body) is bytes:
                    try:
                        body = body.decode()
                    except:
                        body = str(body)
                try:
                    doc = json.loads(body)
                except:
                    doc = body
                return (headers, doc)
