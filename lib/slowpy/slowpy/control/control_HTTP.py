
from slowpy.control import ControlNode
import logging, requests


class HttpNode(ControlNode):
    def __init__(self, url):
        self.url = url

        
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
            response = requests.get(url)
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
            response = requests.post(url, data=content)
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
        def http(self, url):
            try:
                self._http_nodes.keys()
            except:
                self._http_nodes = {}
                
            node = self._http_nodes.get(url, None)
            if node is None:
                node = HttpNode(url)
                self._http_nodes[url] = node

            return node

        return http

    
    
class HttpPathNode(ControlNode):
    def __init__(self, connection, path, **kwargs):
        self.connection = connection
        self.path = path
        
    
    def set(self, value):
        return self.connection.do_post_request(self.path, value)
            
    
    def get(self):
        return self.connection.do_get_request(self.path)


    
def export():
    return [ HttpNode ]
