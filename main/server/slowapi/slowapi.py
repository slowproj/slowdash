# Created by Sanshiro Enomoto on 10 January 2025 #


import typing, json, logging
from urllib.parse import urlparse, parse_qsl, unquote
import inspect


class PathRule:
    def __init__(self, rule:str, func_signature:inspect.Signature, status_code:int=200):
        self.rule_str = rule
        self.status_code = status_code
        self.path = []
        self.path_params = {}  # {pos:int, name:str}
        self.param_attributes = {}  # {name: str, param: inspect.Parameter }
        self.body_param = None

        for elem in rule.split('/'):
            if elem is not None and len(elem) > 0:
                self.path.append(elem)
            
        for pos, elem in enumerate(self.path):
            if len(elem) > 2 and elem[0] == '{' and elem[-1] == '}':
                self.path_params[pos] = elem[1:-1]
                self.path[pos] = None

        for index, pname in enumerate(func_signature.parameters):
            if index == 0:  # self
                continue
            param = func_signature.parameters[pname]
            if param.annotation is bytes:
                self.body_param = pname
            else:
                self.param_attributes[pname] = param

        logging.debug(f'PathRule {rule} --> {self.path}, {self.path_params}, {self.param_attributes}')
            

    def __str__(self):
        return self.rule_str
    

    @staticmethod
    def decode_url(url:str):
        params = {}
        u = urlparse(url)
        
        path = [ unquote(p) for p in u.path.split('/') ]
        while path.count(''):
            path.remove('')

        opts = { unquote(key): unquote(value) for key, value in parse_qsl(u.query) }

        return (path, opts)
    
        
    def match(self, path, opts, body: typing.Optional[bytes]=None):
        if len(path) != len(self.path):
            if len(path) > len(self.path):
                return None
            # maybe a parameter with a default value
            for k in range(len(path), len(self.path)):
                if self.path[k] is not None:
                    return None
        
        params = {}
        for pos, value in enumerate(path):
            if self.path[pos] is None:
                params[self.path_params[pos]] = value
            elif self.path[pos] == value:
                pass
            else:
                return None

        params.update(opts)

        kwargs = {}
        for pname, attr in self.param_attributes.items():
            value = params.get(pname, None)
            if value is None and attr.default is not inspect._empty:
                value = attr.default
            if value is not None and attr.annotation is not inspect._empty:
                try:
                    # BUG: this does not work if the type is "Optional[xxx]"
                    value = attr.annotation(value)
                except Exception as e:
                    logging.warning(f'SlowAPI: incompatible parameter type: {pname}: {e}')
                    return None
            kwargs[pname] = value

        if self.body_param is not None:
            kwargs[self.body_param] = body

        logging.debug(kwargs)
            
        return kwargs
    


class Response:
    status = {
        200: 'OK', 201: 'Created',
        400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found',
        500: 'Internal Server Error', 503: 'Service Unavailable',
    }

    def __init__(self, status_code:int=200, content_type=None, content=None):
        self.status_code = status_code
        self.content_type = content_type
        self.content = None

        if content is not None:
            if content_type is None:
                self.append(content)
            else:
                self.content_type = content_type
                self.content = content

                
    def append(self, content):
        if content is None:
            # no content to append
            pass
        
        elif type(content) is Response:
            # take the content with a larger status_code, or merge the two contents
            response = content
            if response.status_code > self.status_code:
                self.status_code = response.status_code
                self.content_type = response.content_type
                self.content = response.content
            elif self.status_code > response.status_code:
                pass
            else:
                self.append(response.content)

        elif self.status_code >= 400:
            # current content is in an error status; do not append any others
            pass
            
        elif type(content) is list:
            # list contents are appended
            if self.content is None:
                self.content = []
                self.content_type = 'application/json'
            if type(self.content) is list:
                self.content.extend(content)
            else:
                logging.error('SlowAPI: incompatible results cannot be combined (list)')
                
        elif type(content) is dict:
            # dict contents are merged
            if self.content is None:
                self.content = {}
                self.content_type = 'application/json'
            if type(self.content) is dict:
                self.content.update(content)
            else:
                logging.error('SlowAPI: incompatible results cannot be combined (dict)')
                
        elif type(content) is str:
            # string contents are appended after a new line
            if self.content is None:
                self.content = content
                self.content_type = 'text/plain'
            elif type(self.content) is str:
                self.content += '\r\n' + content
            else:
                logging.error('SlowAPI: incompatible results cannot be combined (str)')
            
        else:
            logging.error(f'SlowAPI: invalid content type to append ({type(content)})')

            
    def get_status_code(self):
        if self.content is None:
            return 404
        else:
            return self.status_code
            
        
    def get_status(self):
        if self.content is None:
            return '404 Not Found'
        else:
            return '%d %s' % (self.status_code, self.status.get(self.status_code, 'Unknown Response'))
            
        
    def get_headers(self):
        if self.content_type is None:
            return []
        else:
            return [ ('Content-type',  self.content_type) ]
            
        
    def get_content(self, json_kwargs={}):
        if self.content is None:
            return ''.encode()
        
        if type(self.content) is bytes:
            return self.content
            
        elif type(self.content) is str:
            return self.content.encode()
            
        else:
            return json.dumps(self.content, **json_kwargs).encode()


    def __str__(self):
        if self.get_status_code() >= 400:
            return self.get_status()
        else:
            return self.get_content({"indent":4}).decode()

    
        
class SlowAPI:
    @staticmethod
    def get(path_rule:str, status_code:int=200):
        """decorator for a GET-request handler (method of a subclass of SlowAPI)
        Args:
          - path_rule: path pattern to match
          - status_code: default status code for success
        """
        def wrapper(func):
            func.slowapi_get_rule = PathRule(path_rule, inspect.signature(func), status_code=status_code)
            return func
        return wrapper


    @staticmethod
    def post(path_rule:str, status_code:int=201):
        """decorator for a POST-request handler (method of a subclass of SlowAPI)
        Args:
          - path_rule: path pattern to match
          - status_code: default status code for success
        Note:
          The request body data is passed to the handler via a "bytes" type parameter.
          example:
            @SlowAPI.post('/file/{name}')
            def upload(name:str, body: bytes):
        """
        def wrapper(func):
            func.slowapi_post_rule = PathRule(path_rule, inspect.signature(func), status_code=status_code)
            return func
        return wrapper


    @staticmethod
    def delete(path_rule:str, status_code:int=200):
        """decorator for a DELETE-request handler (method of a subclass of SlowAPI)
        Args:
          - path_rule: path pattern to match
          - status_code: default status code for success
        """
        def wrapper(func):
            func.slowapi_delete_rule = PathRule(path_rule, inspect.signature(func), status_code=status_code)
            return func
        return wrapper


    def __init__(self):
        self.get_handlers = []
        self.post_handlers = []
        self.delete_handlers = []

        self.composite_apis = []

        # Binding URL handlers to the PathRule attached by decorators (@get(PATH) etc).
        # Note that __init__() is called after all the decorators.
        for name, method in inspect.getmembers(type(self), predicate=inspect.isfunction):
            if hasattr(method, 'slowapi_get_rule'):
                self.get_handlers.append((method.slowapi_get_rule, method))
                logging.debug(f'GET {method.slowapi_get_rule} --> {name}()')
            elif hasattr(method, 'slowapi_post_rule'):
                self.post_handlers.append((method.slowapi_post_rule, method))
                logging.debug(f'POST {method.slowapi_post_rule} --> {name}()')
            elif hasattr(method, 'slowapi_delete_rule'):
                self.delete_handlers.append((method.slowapi_delete_rule, method))
                logging.debug(f'DELETE {method.slowapi_delete_rule} --> {name}()')


    def include(api):
        """append another SlowAPI for the composite
        Parameters:
          - api: an instance of SlowAPI
        """
        self.composite_apis.append(api)
        

    def handle_get_request(self, url):
        """handle GET request
        Parameters:
          - url: URL string, or a tuple of (path, opts) by PathRule.decode_url(url)
        Returns:
          - Response object
        """
        if type(url) is str:
            url = PathRule.decode_url(url)
        response = Response()
        
        response.append(self._handle_request(self.get_handlers, url))
        for api in self.composite_apis:
            response.append(api.handle_get_request(url))
        return response
        

    def handle_post_request(self, url, body:bytes):
        """handle POST request
        Parameters:
          - url: URL string, or a tuple of (path, opts) by PathRule.decode_url(url)
          - body: request body
        Returns:
          - Response object
        """
        if type(url) is str:
            url = PathRule.decode_url(url)
        response = Response()
        
        response.append(self._handle_request(self.post_handlers, url, body))
        for api in self.composite_apis:
            response.append(api.handle_post_request(url, body))
        return response
    

    def handle_delete_request(self, url:str):
        """handle DELETE request
        Parameters:
          - url: URL string, or a tuple of (path, opts) by PathRule.decode_url(url)
        Returns:
          - Response object
        """
        if type(url) is str:
            url = PathRule.decode_url(url)
        response = Response()
        
        response.append(self._handle_request(self.delete_handlers, url))
        for api in self.composite_apis:
            response.append(api.handle_delete_request(url))
        return response


    def _handle_request(self, handlers, url, body:typing.Optional[bytes]=None):
        """
        Args:
          - handlers: self.XXX_handlers where XXX is "get", "post", or "delete"
          - url: tuple of (path, opts), which is a return values of PathRule.decode(url)
          - body: request body
        Returns:
          - a Response object, or
          - None if there is no handler for the URL
        """
        path, opts = url
        response = None
        
        for rule, handler in handlers:
            params = rule.match(path, opts, body)
            if params is None:
                continue
            
            this_result = handler(self, **params)
            if this_result is None:
                continue
            
            if response is None:
                response = Response(status_code=rule.status_code)
            response.append(this_result)

        return response


    def __call__(self, environ, start_response):
        """WSGI interface
        Args: see the WSGI specification
        """
        path = environ.get('PATH_INFO', '/')
        query = environ.get('QUERY_STRING', '')
        method = environ.get('REQUEST_METHOD', 'GET')
        content_length = environ.get('CONTENT_LENGTH', '')
        url = path + ('?' + query if len(query) > 0 else '')

        if method == 'GET':
            response = self.handle_get_request(url)
            
        elif method == 'POST':
            try:
                content_length = int(content_length)
            except:
                logging.error(f'WSGI_POST: bad content length: {content_length}')
                start_response('400 Bad Request', [])
                return [ b'' ]
            if content_length > 1024*1024*1024:
                logging.error(f'WSGI_POST: content length too large: {content_length}')
                start_response('507 Insufficient Storage', [])
                return [ b'' ]
            body = environ['wsgi.input'].read(content_length)
            response = self.handle_post_request(url, body)
        
        elif method == 'DELETE':
            response = self.handle_delete_request(url)
            
        else:
            start_response('500 Internal Server Error', [])
            return [ b'' ]

    
        if response is None:
            start_response('404 Not Found', [])
            return [ b'' ]

        start_response(response.get_status(), response.get_headers())
        return [ response.get_content() ]
