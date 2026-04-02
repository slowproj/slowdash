# Created by Sanshiro Enomoto on 30 August 2024 #
# Updated by Sanshiro Enomoto on 1 April 2025 for Asyc (requests -> httpx)


import json, logging
from slowpy.control import ControlNode, ControlVariableNode, ControlException


class AsyncHttpNode(ControlNode):
    def __init__(self, url, auth=None):
        self.url = url
        self.auth = auth  # None or tuple of (user, pass)

        try:
            import httpx
            if self.auth is not None:
                self.client = httpx.AsyncClient(auth=auth)
            else:
                self.client = httpx.AsyncClient()
        except Exception as e:
            logging.error(f'unable to import "requests" module; maybe not installed?: {e}')
            self.client = None


    async def aio_close(self):
        if self.client is not None:
            await self.client.aclose()

            
    @classmethod
    def _node_creator_method(cls):
        def async_http(self, url, **kwargs):
            return AsyncHttpNode(url, **kwargs)

        return async_http

    
    async def aio_set(self, value):
        return await self.aio_do_post_request(path='', content=value)

    async def aio_get(self):
        return await self.aio_do_get_request(path='')


    ## methods ##    
    async def aio_do_get_request(self, path):
        if self.client is None:
            return None
        
        if path is None or len(path) == 0:
            url = self.url
        else:
            url = self.url + path
            
        try:
            response = await self.client.get(url)
        except Exception as e:
            raise ControlException('unable to fetch URL resource "%s": %s' % (url, str(e)))
        if response.status_code != 200:
            raise ControlException('unable to fetch URL resource "%s": status %d' % (url, response.status_code))

        return response.content
    
        
    async def aio_do_post_request(self, path, content):
        if self.client is None:
            return None
        
        if path is None or len(path) == 0:
            url = self.url
        else:
            url = self.url + path
        print(f'POST: {url}')
            
        try:
            response = await self.client.post(url, data=content)
        except Exception as e:
            raise ControlException('unable to fetch URL resource "%s": %s' % (url, str(e)))
        if response.status_code >= 300:
            raise ControlException('unable to fetch URL resource "%s": status %d' % (url, response.status_code))

        return response.status_code
    
        
    ## child nodes ##
    def path(self, path, **kwargs):
        return HttpPathNode(self, path, **kwargs)
    

    
class HttpPathNode(ControlNode):
    def __init__(self, connection, path, **kwargs):
        self.connection = connection
        
        opts = '&'.join([f'{k}={v}' for k,v in kwargs.items()])
        if len(opts) == 0:
            self.path = path
        elif '?' in path:
            self.path = path + '&' + opts
        else:
            self.path = path + '?' + opts
        
        
    async def aio_set(self, value):
        return await self.connection.aio_do_post_request(self.path, value)
            
    async def aio_get(self):
        return await self.connection.aio_do_get_request(self.path)

    
    ## child nodes ##
    def value(self, **kwargs):
        return HttpValuePathNode(self, **kwargs)

    def json(self, **kwargs):
        return HttpJsonPathNode(self, **kwargs)
    

    
class HttpValuePathNode(ControlVariableNode):
    def __init__(self, path_node, **kwargs):
        self.path_node = path_node
        
    async def aio_set(self, value):
        return await self.path_node.aio_set(value)
            
    async def aio_get(self):
        content = await self.path_node.aio_get()
        if content is None:
            return None
        
        return content.decode()
            
    
    
class HttpJsonPathNode(ControlNode):
    def __init__(self, path_node, **kwargs):
        self.path_node = path_node
        
    
    async def aio_set(self, value):
        return await self.path_node.aio_set(json.dumps(value))
            
    
    async def aio_get(self):
        content = await self.path_node.aio_get()
        if content is None:
            return None
        
        try:
            return json.loads(content.decode())
        except Exception as e:
            raise ControlException('bad JSON document: %s' % str(e))
