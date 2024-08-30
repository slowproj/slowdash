
from slowpy.control import ControlNode
import requests, json, logging


class HttpNode(ControlNode):
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
            if response.status_code != 200:
                logging.error('unable to fetch URL resource "%s": status %d' % (url, response.status_code))
                response = None
            else:
                logging.info('URL resource fetched: %d: %s' % (response.status_code, url))
        except Exception as e:
            response = None
            logging.error('unable to fetch URL resource "%s": %s' % (url, str(e)))
            
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
            if response.status_code != 200:
                logging.error('unable to fetch URL resource "%s": status %d' % (url, response.status_code))
                response = None
            else:
                logging.info('URL resource fetched: %d: %s' % (response.status_code, url))
        except Exception as e:
            response = None
            logging.error('unable to fetch URL resource "%s": %s' % (url, str(e)))
            
        return response.content.decode()
    
        
    ## child nodes ##
    def path(self, path, **kwargs):
        return HttpPathNode(self, path, **kwargs)
    

    @classmethod
    def _node_creator_method(cls):
        def http(self, url, **kwargs):
            return HttpNode(url, **kwargs)

        return http

    
    
class HttpPathNode(ControlNode):
    def __init__(self, connection, path, **kwargs):
        self.connection = connection
        self.path = path
        
    
    def set(self, value):
        return self.connection.do_post_request(self.path, value)
            
    
    def get(self):
        return self.connection.do_get_request(self.path)

    
    ## child nodes ##
    def json(self, **kwargs):
        return HttpJaonPathNode(self, **kwargs)
    

    
class HttpJsonPathNode(ControlNode):
    def __init__(self, connection, **kwargs):
        self.connection = connection
        
    
    def set(self, value):
        return self.connection.set(json.dumps(value))
            
    
    def get(self):
        content = self.connection.get(self.path)
        try:
            return json.loads(content)
        except Exception as e:
            logging.error('bad JSON document')
            return None
            
    
    
def export():
    return [ HttpNode ]
