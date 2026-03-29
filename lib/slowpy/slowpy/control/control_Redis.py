# Created by Sanshiro Enomoto on 22 May 2024 #


import time, redis, json
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

        
    def __del__(self):
        self.close()


    def open(self):
        if self.redis is not None:
            return True
        
        try:
            import redis
        except Exception as e:
            logger.warning('Redis: radis python module import error: %s' % str(e))
            return False
        
        try:
            self.redis = redis.from_url(
                self.url,
                decode_responses=self.decode_response,
                health_check_interval=60,
                **self.kwargs
            )
            self.redis.ping()
        except Exception as e:
            logging.warning(f'Redis: unable to connect to server: {self.url}')
            try:
                self.redis.close()
            except:
                pass
            self.redis = None
        else:
            logging.warning(f'Redis: connected: {self.url}')

        return self.redis is not None
        
            
    def close(self):
        if self.redis is not None:
            self.redis.close()

        
    def set(self, value):
        pass

    
    def get(self):
        return self.redis.info()

    
    ## Redis specific functions ##
    def get_info(self):
        if not self.open():
            return None
        return self.redis.info()

    
    def get_keys(self, pattern='*'):
        if not self.open():
            return None
        return self.redis.keys(pattern)

    
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
        def redis(self, url):
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

        return redis

    
    
class RedisStringNode(ControlNode):
    def __init__(self, redis_node, name):
        self.redis_node = redis_node
        self.name = name
            
    def set(self, value):
        if not self.redis_node.open():
            return None
        self.redis_node.redis.set(self.name, value)
    
    def get(self):
        if not self.redis_node.open():
            return None
        return self.redis_node.redis.get(self.name)

    def do_incr(self, amount=1):
        if not self.redis_node.open():
            return None
        return self.redis_node.redis.incr(self.name, amount)
    

    
class RedisHashNode(ControlNode):
    def __init__(self, redis_node, name):
        self.redis_node = redis_node
        self.name = name
            
    def set(self, value):
        if not self.redis_node.open():
            return None
        if type(value) == dict:
            self.redis_node.redis.hset(self.name, mapping=value)
            
    def get(self):
        if not self.redis_node.open():
            return None
        return self.redis_node.redis.hgetall(self.name)
    
    # child nodes #
    def field(self, fieldname):
        return RedisHashFieldNode(self.redis_node, self.name, fieldname)

    
    
class RedisHashFieldNode(ControlNode):
    def __init__(self, redis_node, name, fieldname):
        self.redis_node = redis_node
        self.name = name
        self.fieldname = fieldname
        
    def set(self, value):
        if not self.redis_node.open():
            return None
        self.redis_node.redis.hset(self.name, self.fieldname, value)

    def get(self):
        if not self.redis_node.open():
            return None
        return self.redis_node.redis.hget(self.name, self.fieldname)

    
    
class RedisJsonNode(ControlNode):
    def __init__(self, redis_node, name, base='$'):
        self.redis_node = redis_node
        self.name = name
        self.base = base
    
    def set(self, value):
        if not self.redis_node.open():
            return None
        self.redis_node.redis.json().set(self.name, self.base, value)

    def get(self):
        if not self.redis_node.open():
            return None
        result = self.redis_node.redis.json().get(self.name, self.base)
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
    
    def set(self, value):
        if not self.redis_node.open():
            return None
        for t,x in value:
            self.redis_node.redis.ts().add(self.name, t, x)

    def get(self):
        if not self.redis_node.open():
            return None
        to = self.to if self.to > 0 else time.time() + self.to
        start = to - self.length
        return self.redis_node.redis.ts().range(self.name, int(1000*start), int(1000*to))
       
    ## child nodes ##
    # redis().ts(name).current() to set()
    def current(self):  
        return RedisTimeseriesCurrentNode(self)

    # redis().ts(name).last() to get()
    def last(self):
        return RedisTimeseriesLastNode(self)

    
    
class RedisTimeseriesCurrentNode(ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    def set(self, value):
        self.parent.set([(int(1000*time.time()), value)])

    def get(self):
        return None
        
    
    
class RedisTimeseriesLastNode(ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    def set(self, value):
        pass

    def get(self):
        if not self.parent.redis_node.open():
            return None
        if self.parent.to == 0:
            return self.parent.redis_node.redis.ts().get(self.parent.name)
        else:
            to = self.parent.to if self.parent.to > 0 else time.time() + self.parent.to
            start = to - self.parent.length
            ts = self.parent.redis_node.redis.ts().revrange(self.parent.name, int(1000*start), int(1000*to), count=1)
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
    
    def set(self, value):
        pass

    def get(self):
        last = self.parent.get()
        if last is None:
            return None
        return last[1]


    
class RedisTimeseriesLastTimeNode(ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    def set(self, value):
        pass

    def get(self):
        last = self.parent.get()
        if last is None:
            return None
        return last[0]/1000.0


    
class RedisTimeseriesLastLapseNode(ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    def set(self, value):
        pass

    def get(self):
        last = self.parent.get()
        if last is None:
            return None
        return time.time() - last[0]/1000.0


class RedisPublisherNode(ControlNode):
    def __init__(self, redis_node, topic):
        self.redis_node = redis_node
        self.topic = topic


    def set(self, value):
        if not self.redis_node.open():
            return None
        try:
            self.redis_node.redis.publish(self.topic, value)
        except Exception as e:
            logger.warning(f'Redis: redis.publish(): {e}')


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


    def __del__(self):
        if self.pubsub is not None:
            try:
                self.pubsub.close()
            except:
                pass
        
        
    def get(self):
        if self.pubsub is None:
            if self.redis_node.open():
                try:
                    self.pubsub = self.redis_node.redis.pubsub()
                    self.pubsub.psubscribe(self.topic_pattern)
                except Exception as e:
                    logger.warning(f'Redis: psubscribe(): {e}')
                    try:
                        self.pubsub.close()
                    except:
                        pass
                    self.pubsub = None
                else:
                    if self.disconnected:
                        self.disconnected = False
                        logger.info(f'Redis: reconnected')

        if self.pubsub is None:
            time.sleep(1)
            return None

        try:
            if self.timeout is None or self.timeout < 0:
                return self.pubsub.get_message(ignore_subscribe_messages=True)
            else:
                return self.pubsub.get_message(ignore_subscribe_messages=True, timeout=self.timeout)
        except Exception as e:
            try:
                self.pubsub.close()
            except:
                pass
            self.pubsub = None
            if not self.disconnected:
                self.disconnected = True
                logger.warning(f'Redis: redis.pubsub.get_message(): {e}')
            
        time.sleep(1)
        return None


    ## child nodes ##
    # redis().subscriber(topic_pettern).json()
    def json(self):
        return RedisSubscriberJsonNode(self)
        

    
class RedisPublisherJsonNode(ControlNode):
    def __init__(self, publisher_node, headers = None):
        self.publisher_node = publisher_node
        self.headers = dict(headers or {})
        

    def set(self, value):
        try:
            doc = json.dumps(value)
        except Exception as e:
            logger.warning('AsyncRedis: publisher(): unable to convert to JSON: {e}')
            return None
        
        return self.publisher_node.set(doc)



class RedisSubscriberJsonNode(ControlNode):
    def __init__(self, subscriber_node):
        self.subscriber_node = subscriber_node
        

    def get(self):
        while True:
            message = self.subscriber_node.get()
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
            
