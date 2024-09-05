
import time, traceback
import slowpy.control as spc


class RedisNode(spc.ControlNode):
    def __init__(self, url, **kwargs):
        # retries up to 60 sec, for docker-compose etc.
        self.redis = None

        try:
            import redis
        except Exception as e:
            raise spc.ControlException('radis python module import error: %s' % str(e))
        
        for i in range(12):
            try:
                self.redis = redis.from_url(url, decode_responses=True, **kwargs)
                keys =  self.redis.keys()
                break
            except Exception as e:
                print('Redis not connected: %s: retry in 5 sec' % url)
                time.sleep(5)
        else:
            print(traceback.format_exc())
            self.redis = None
        
        if self.redis is None:
            raise spc.ControlException('Redis not loaded: %s' % url)

        
    def __del__(self):
        pass

    
    def set(self, value):
        pass

    
    def get(self):
        return self.redis.info()

    
    ## Redis specific functions ##
    def get_info(self):
        return self.redis.info()

    
    def get_keys(self, pattern='*'):
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
                    raise spc.ControlException('Redis URL not provided')
                else:
                    url = keys[-1]
            node = self._redis_nodes.get(url, None)
                
            if node is None:
                node = RedisNode(url)
                self._redis_nodes[url] = node

            return node

        return redis

    
    
class RedisStringNode(spc.ControlNode):
    def __init__(self, redis, name):
        self.redis = redis
        self.name = name
            
    def set(self, value):
        self.redis.set(self.name, value)
    
    def get(self):
        return self.redis.get(self.name)

    def do_incr(self, amount=1):
        return self.redis.incr(self.name, amount)
    

    
class RedisHashNode(spc.ControlNode):
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

    
    
class RedisHashFieldNode(spc.ControlNode):
    def __init__(self, redis, name, fieldname):
        self.redis = redis
        self.name = name
        self.fieldname = fieldname
        
    def set(self, value):
        self.redis.hset(self.name, self.fieldname, value)

    def get(self):
        return self.redis.hget(self.name, self.fieldname)

    
    
class RedisJsonNode(spc.ControlNode):
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

    
    
class RedisTimeseriesNode(spc.ControlNode):
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
    # Redis.ts(name).current() to set()
    def current(self):  
        return RedisTimeseriesCurrentNode(self)

    # Redis.ts(name).last() to get()
    def last(self):
        return RedisTimeseriesLastNode(self)

    
    
class RedisTimeseriesCurrentNode(spc.ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    def set(self, value):
        self.parent.set([(int(1000*time.time()), value)])

    def get(self):
        return None
        
    
    
class RedisTimeseriesLastNode(spc.ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    def set(self, value):
        pass

    def get(self):
        if self.parent.to == 0:
            return self.parent.redis.ts().get(self.parent.name)
        else:
            to = self.parent.to if self.parent.to > 0 else time.time() + self.parent.to
            start = to - self.parent.length
            ts = self.parent.redis.ts().revrange(self.parent.name, int(1000*start), int(1000*to), count=1)
            if len(ts) > 0:
                return ts[0]
            else:
                return (None, None)
        
    ## child nodes ##
    # Redis.ts(name).last().time()
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
    
    def set(self, value):
        pass

    def get(self):
        return self.parent.get()[1]


    
class RedisTimeseriesLastTimeNode(spc.ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    def set(self, value):
        pass

    def get(self):
        return self.parent.get_tx()[0]/1000.0


    
class RedisTimeseriesLastLapseNode(spc.ControlNode):
    def __init__(self, parent):
        self.parent = parent
    
    def set(self, value):
        pass

    def get(self):
        return time.time() - self.parent.get_tx()[0]/1000.0
