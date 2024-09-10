# Created by Sanshiro Enomoto on 30 August 2024 #


import requests, json
import slowpy.control as spc


class HttpNode(spc.ControlNode):
    def __init__(self, url, auth=None):
        self.url = url
        self.auth = auth  # None or tuple of (user, pass)
        
    @classmethod
    def _node_creator_method(cls):
        def http(self, url, **kwargs):
            return HttpNode(url, **kwargs)

        return http

    
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
            raise spc.ControlException('unable to fetch URL resource "%s": %s' % (url, str(e)))
        if response.status_code != 200:
            raise spc.ControlException('unable to fetch URL resource "%s": status %d' % (url, response.status_code))

        return response.content.decode()
    
        
    def do_post_request(self, path, content):
        if path is None or len(path) == 0:
            url = self.url
        else:
            url = self.url + path
        print(f'POST: {url}')
            
        try:
            if self.auth is None:
                response = requests.post(url, data=content)
            else:
                response = requests.post(url, data=content, auth=self.auth)
        except Exception as e:
            raise spc.ControlException('unable to fetch URL resource "%s": %s' % (url, str(e)))
        if response.status_code >= 300:
            raise spc.ControlException('unable to fetch URL resource "%s": status %d' % (url, response.status_code))

        return response.status_code
    
        
    ## child nodes ##
    def path(self, path, **kwargs):
        return HttpPathNode(self, path, **kwargs)
    

    
class HttpPathNode(spc.ControlNode):
    def __init__(self, connection, path, **kwargs):
        self.connection = connection
        
        opts = '&'.join([f'{k}={v}' for k,v in kwargs.items()])
        if len(opts) == 0:
            self.path = path
        elif '?' in path:
            self.path = path + '&' + opts
        else:
            self.path = path + '?' + opts
        
        
    def set(self, value):
        return self.connection.do_post_request(self.path, value)
            
    def get(self):
        return self.connection.do_get_request(self.path)

    
    ## child nodes ##
    def value(self, **kwargs):
        return HttpValuePathNode(self, **kwargs)

    def json(self, **kwargs):
        return HttpJsonPathNode(self, **kwargs)
    

    
class HttpValuePathNode(spc.ControlVariableNode):
    def __init__(self, path_node, **kwargs):
        self.path_node = path_node
        
    def set(self, value):
        return self.path_node.set(value)
            
    def get(self):
        return self.path_node.get()
            
    
    
class HttpJsonPathNode(spc.ControlNode):
    def __init__(self, path_node, **kwargs):
        self.path_node = path_node
        
    
    def set(self, value):
        return self.path_node.set(json.dumps(value))
            
    
    def get(self):
        content = self.path_node.get()
        try:
            return json.loads(content)
        except Exception as e:
            raise spc.ControlException('bad JSON document: %s' % str(e))
