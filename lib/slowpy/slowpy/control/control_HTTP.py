
import requests, json
import slowpy.control as slc


class HttpNode(slc.ControlNode):
    def __init__(self, url, auth=None):
        self.url = url
        self.auth = auth  # None or tuple of (user, pass)

        
    def __del__(self):
        pass

        
    def set(self, value):
        return self.do_post_request(path='', content=value)

    
    def get(self):
        return self.do_get_request(path='')


    ## methods ##    
    def do_get_request(self, path):
        if path is None or len(path) == 0:
            url = self.url
        else:
            url = self.url + path
            
        try:
            if self.auth is None:
                response = requests.get(url)
            else:
                response = requests.get(url, auth=self.auth)
        except Exception as e:
            raise slc.ControlExcetion('unable to fetch URL resource "%s": %s' % (url, str(e)))
        if response.status_code != 200:
            raise slc.ControlException('unable to fetch URL resource "%s": status %d' % (url, response.status_code))

        return response.content.decode()
    
        
    def do_post_request(self, path, content):
        if path is None or len(path) == 0:
            url = self.url
        else:
            url = self.url + path
            
        try:
            if self.auth is None:
                response = requests.post(url, data=content)
            else:
                response = requests.post(url, data=content, auth=self.auth)
        except Exception as e:
            raise slc.ControlException('unable to fetch URL resource "%s": %s' % (url, str(e)))
        if response.status_code != 200:
            raise slc.ControlException('unable to fetch URL resource "%s": status %d' % (url, response.status_code))

        return response.content.decode()
    
        
    ## child nodes ##
    def path(self, path, **kwargs):
        return HttpPathNode(self, path, **kwargs)
    

    @classmethod
    def _node_creator_method(cls):
        def http(self, url, **kwargs):
            return HttpNode(url, **kwargs)

        return http

    
    
class HttpPathNode(slc.ControlNode):
    def __init__(self, connection, path, **kwargs):
        self.connection = connection
        self.path = path
        
    
    def set(self, value):
        return self.connection.do_post_request(self.path, value)
            
    
    def get(self):
        return self.connection.do_get_request(self.path)

    
    ## child nodes ##
    def value(self, **kwargs):
        return HttpValuePathNode(self, **kwargs)

    
    def json(self, **kwargs):
        return HttpJaonPathNode(self, **kwargs)
    

    
class HttpValuePathNode(slc.ControlValueNode):
    def __init__(self, connection, **kwargs):
        self.connection = connection
        
    
    def set(self, value):
        return self.connection.set(json.dumps(value))
            
    
    def get(self):
        return self.connection.get(self.path)
            
    
    
class HttpJsonPathNode(slc.ControlNode):
    def __init__(self, connection, **kwargs):
        self.connection = connection
        
    
    def set(self, value):
        return self.connection.set(json.dumps(value))
            
    
    def get(self):
        content = self.connection.get(self.path)
        try:
            return json.loads(content)
        except Exception as e:
            raise slc.ControlException('bad JSON document: %s' % str(e))
            
    
    
def export():
    return [ HttpNode ]
