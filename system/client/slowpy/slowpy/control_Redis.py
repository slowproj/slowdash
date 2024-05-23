
import time, logging
from slowpy.control import ControlNode


class RedisNode(ControlNode):
    def __init__(self, parent, url, **kwargs):
        # retries up to 60 sec, for docker-compose etc.
        self.redis = None
        
        import redis
        for i in range(12):
            try:
                self.redis = redis.from_url(url, decode_responses=True, **kwargs)
                keys =  self.redis.keys()
                break
            except Exception as e:
                logging.info(e)
                logging.warn('Redis not connected: %s: retry in 5 sec' % url)
                time.sleep(5)
        else:
            self.redis = None
        
        if self.redis is None:
            logging.error('Redis not loaded: %s' % url)
            return
    
    def __del__(self):
        pass
        
    def set(self, value):
        pass

    def get(self):
        return self.redis.info()

    ## Redis specific functions ##
    def info(self):
        return self.redis.info()

    def keys(self, pattern='*'):
        return self.redis.keys(pattern)
    
    ## child nodes ##
    def string(self, name):
        return RedisStringNode(self.redis, name)
    
    def hash(self, name):
        return RedisHashNode(self.redis, name)
    
    def json(self, name, base='$'):
        return RedisJsonNode(self.redis, name, base)
    
    def ts(self, name, length=3600, to=0):
        return RedisTimeseriesNode(self.redis, name, length, to)
    

    @classmethod
    def _node_creator_method(cls):
        def redis(self, url=None):
            try:
                keys = [ key for key in self._redis_nodes.keys() ]
            except:
                self._redis_nodes = {}
                keys = []
            if url is None:
                if len(keys) == 0:
                    logging.error('Redis URL not provided')
                    return None
                else:
                    url = keys[-1]
            node = self._redis_nodes.get(url, None)
                
            if node is None:
                node = RedisNode(self, url)
                self._redis_nodes[url] = node  # even if node is None; not to repeat the initialization error
                if node.redis is None:
                    node = None
                    logging.error('unable to connect to Redis: %s' % url)

            return node

        return redis

    
    
class RedisStringNode(ControlNode):
    def __init__(self, redis, name):
        self.redis = redis
        self.name = name
            
    def set(self, value):
        self.redis.set(self.name, value)
    
    def get(self):
        return self.redis.get(self.name)

    def incr(self, amount=1):
        return self.redis.incr(self.name, amount)
    

    
class RedisHashNode(ControlNode):
    def __init__(self, redis, name):
        self.redis = redis
        self.name = name
            
    def set(self, value):
        if type(value) == dict:
            self.redis.hset(self.name, mapping=value)
            
    def get(self):
        return self.redis.hgetall(self.name)
    
    # child nodes #
    def field(self, fieldname):
        return RedisHashFieldNode(self.redis, self.name, fieldname)

    
    
class RedisHashFieldNode(ControlNode):
    def __init__(self, redis, name, fieldname):
        self.redis = redis
        self.name = name
        self.fieldname = fieldname
        
    def set(self, value):
        self.redis.hset(self.name, self.fieldname, value)

    def get(self):
        return self.redis.hget(self.name, self.fieldname)

    
    
class RedisJsonNode(ControlNode):
    def __init__(self, redis, name, base='$'):
        self.redis = redis
        self.name = name
        self.base = base
    
    def set(self, value):
        self.redis.json().set(self.name, self.base, value)

    def get(self):
        result = self.redis.json().get(self.name, self.base)
        if type(result) is list:
            if len(result) == 0:
                return None
            elif len(result) == 1:
                return result[0]
        return result

    ## child nodes ##
    # redis().json(name).node(name)
    def node(self, name):
        return RedisJsonNode(self.redis, self.name, self.base + '.' + name)

    
    
class RedisTimeseriesNode(ControlNode):
    def __init__(self, redis, name, length=3600, to=0):
        self.redis = redis
        self.name = name
        self.length = length
        self.to = to    # zero for "now", positive for UNIX timestamp, negative for time to "now"
    
    def set(self, value):
        for t,x in value:
            self.redis.ts().add(self.name, t, x)

    def get(self):
        to = self.to if self.to > 0 else time.time() + self.to
        start = to - self.length
        return self.redis.ts().range(self.name, int(1000*start), int(1000*to))
       
    ## child nodes ##
    # Redis.ts(name).last()
    def last(self):
        return RedisTimeseriesLastNode(self)

    
    
class RedisTimeseriesLastNode(ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    def set(self, value):
        self.parent.set([(int(1000*time.time()), value)])

    def get(self):
        return self.get_tx()[1]
        
    def get_tx(self):
        if self.parent.to == 0:
            return self.parent.redis.ts().get(self.parent.name)
        else:
            ts = self.parent.get()
            if len(ts) > 0:
                return ts[-1]
            else:
                return (None, None)
        
    ## child nodes ##
    # Redis.ts(name).last().time()
    def time(self):
        return RedisTimeseriesLastTimeNode(self)

    # Redis.ts(name).last().lapse()    
    def lapse(self):
        return RedisTimeseriesLastLapseNode(self)

    
    
class RedisTimeseriesLastTimeNode(ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    def set(self, value):
        pass

    def get(self):
        return self.parent.get_tx()[0]/1000.0

    
class RedisTimeseriesLastLapseNode(ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    def set(self, value):
        pass

    def get(self):
        return time.time() - self.parent.get_tx()[0]/1000.0
    
    
def export():
    return [ RedisNode ]
