
import time, logging
from slowpy.control import Endpoint


class RedisEndpoint(Endpoint):
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

    # child endopints #
    def string(self, name):
        return RedisStringEndpoint(self.redis, name)
    
    def hash(self, name):
        return RedisHashEndpoint(self.redis, name)
    
    def json(self, name, base='$'):
        return RedisJsonEndpoint(self.redis, name, base)
    

    @classmethod
    def _endpoint_creator_method(cls):
        def redis(self, url=None):
            try:
                keys = [ key for key in self._redis_endpoints.keys() ]
            except:
                self._redis_endpoints = {}
                keys = []
            if url is None:
                if len(keys) == 0:
                    logging.error('Redis URL not provided')
                    return None
                else:
                    url = keys[-1]
            endpoint = self._redis_endpoints.get(url, None)
                
            if endpoint is None:
                endpoint = RedisEndpoint(self, url)
                self._redis_endpoints[url] = endpoint  # even if endpoint is None; not to repeat the initialization error
                if endpoint.redis is None:
                    endpoint = None
                    logging.error('unable to connect to Redis: %s' % url)

            return endpoint

        return redis

    
    
class RedisStringEndpoint(Endpoint):
    def __init__(self, redis, name):
        self.redis = redis
        self.name = name
            
    def set(self, value):
        self.redis.set(self.name, value)
    
    def get(self):
        return self.redis.get(self.name)

    def incr(self, amount=1):
        return self.redis.incr(self.name, amount)
    

    
class RedisHashEndpoint(Endpoint):
    def __init__(self, redis, name):
        self.redis = redis
        self.name = name
            
    def set(self, value):
        if type(value) == dict:
            self.redis.hset(self.name, mapping=value)
            
    def get(self):
        return self.redis.hgetall(self.name)
    
    # child endopints #
    def field(self, fieldname):
        return RedisHashFieldEndpoint(self.redis, self.name, fieldname)

    
    
class RedisHashFieldEndpoint(Endpoint):
    def __init__(self, redis, name, fieldname):
        self.redis = redis
        self.name = name
        self.fieldname = fieldname
        
    def set(self, value):
        self.redis.hset(self.name, self.fieldname, value)

    def get(self):
        return self.redis.hget(self.name, self.fieldname)

    
    
class RedisJsonEndpoint(Endpoint):
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

    # child endopints #
    def node(self, name):
        return RedisJsonEndpoint(self.redis, self.name, self.base + '.' + name)

    
    
def export():
    return [ RedisEndpoint ]
