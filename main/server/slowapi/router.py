# Created by Sanshiro Enomoto on 10 January 2025 #


import typing, inspect, copy, logging
from urllib.parse import urlparse, parse_qsl, unquote

from .model import JSON
from .request import Request
from .response import Response
from .server import run as run_server



class PathRule:
    def __init__(self, rule:str, func_signature:inspect.Signature, status_code:int=200):
        self.rule_str = rule
        self.status_code = status_code
        self.path = []
        self.path_params = {}  # {pos:int, name:str}
        self.param_attributes = {}  # {name: str, param: inspect.Parameter }
        self.bytes_body_param = None
        self.json_body_param = None
        self.path_param = None
        self.query_param = None

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
            if param.annotation is bytes:   # to store request body
                self.bytes_body_param = pname
            if param.annotation is JSON:   # to decode request body as JSON
                self.json_body_param = pname
            elif param.annotation is list:  # to store URL path
                self.path_param = pname
            elif param.annotation is dict:  # to store URL query
                self.query_param = pname
            else:
                self.param_attributes[pname] = param

        logging.debug(f'PathRule {rule} --> {self.path}, {self.path_params}, {self.param_attributes}')
            

    def __str__(self):
        return self.rule_str
    

    def match(self, request:Request):
        # length match
        if len(request.path) != len(self.path):
            # longer path: can be stored in the "path" argument
            if (self.path_param is None) and (len(request.path) > len(self.path)):
                return None
            # shorter path: maybe a parameter with a default value
            for k in range(len(request.path), len(self.path)):
                if self.path[k] is not None:
                    return None
        
        # path name/param match
        params = {}
        for pos, value in enumerate(request.path):
            if pos >= len(self.path):
                pass
            elif self.path[pos] is None:
                params[self.path_params[pos]] = value
            elif self.path[pos] == value:
                pass
            else:
                return None

        params.update(request.query)

        # argument match / import
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
                    logging.warning(f'App: incompatible parameter type: {pname}: {e}')
                    return None
            kwargs[pname] = value
            
        # special arguments
        if self.bytes_body_param is not None:
            kwargs[self.bytes_body_param] = request.body
        if self.json_body_param is not None:
            doc = JSON(request.body)
            if doc.json() is None:
                return None
            else:
                kwargs[self.json_body_param] = doc
        if self.path_param is not None:
            kwargs[self.path_param] = copy.deepcopy(request.path)
        if self.query_param is not None:
            kwargs[self.query_param] = copy.deepcopy(request.query)

        return kwargs
    


def get(path_rule:str, status_code:int=200):
    """decorator to make a GET-request handler (method of a subclass of App)
    Args:
      - path_rule: path pattern to match
      - status_code: default status code for success
    """
    def wrapper(func):
        if not hasattr(func, 'slowapi_get_rule'):
            func.slowapi_get_rule = PathRule(path_rule, inspect.signature(func), status_code=status_code)
        return func
    return wrapper


def post(path_rule:str, status_code:int=201):
    """decorator to make a POST-request handler (method of a subclass of App)
    Args:
      - path_rule: path pattern to match
      - status_code: default status code for success
    """
    def wrapper(func):
        if not hasattr(func, 'slowapi_post_rule'):
            func.slowapi_post_rule = PathRule(path_rule, inspect.signature(func), status_code=status_code)
        return func
    return wrapper


def delete(path_rule:str, status_code:int=200):
    """decorator to make a DELETE-request handler (method of a subclass of App)
    Args:
      - path_rule: path pattern to match
      - status_code: default status code for success
    """
    def wrapper(func):
        if not hasattr(func, 'slowapi_delete_rule'):
            func.slowapi_delete_rule = PathRule(path_rule, inspect.signature(func), status_code=status_code)
        return func
    return wrapper

    

class App:
    """SlowAPI Application: Base class for user applications
    Note:
      - To avoid possible name collisions, all attributes are prefixed with slowapi_,
      - except for __call__() and run().
    """
    def __init__(self):
        self.slowapi_get_handlers = []
        self.slowapi_post_handlers = []
        self.slowapi_delete_handlers = []

        self.slowapi_composite_apps = []

        # Binding URL handlers to the PathRule attached by decorators (@get(PATH) etc).
        # Note that __init__() is called after all the decorators.
        for name, method in inspect.getmembers(type(self), predicate=inspect.isfunction):
            if hasattr(method, 'slowapi_get_rule'):
                self.slowapi_get_handlers.append((method.slowapi_get_rule, method))
                logging.debug(f'GET {method.slowapi_get_rule} --> {name}()')
            elif hasattr(method, 'slowapi_post_rule'):
                self.slowapi_post_handlers.append((method.slowapi_post_rule, method))
                logging.debug(f'POST {method.slowapi_post_rule} --> {name}()')
            elif hasattr(method, 'slowapi_delete_rule'):
                self.slowapi_delete_handlers.append((method.slowapi_delete_rule, method))
                logging.debug(f'DELETE {method.slowapi_delete_rule} --> {name}()')


    def _slowapi_handle_request(self, handlers, request:Request) -> typing.Optional[Response]:
        """
        Args:
          - handlers: self.slowapi_XXX_handlers where XXX is "get", "post", or "delete"
          - request: a Request object (contains path, query, headers, and optionally a body)
        Returns:
          - a Response object, or
          - None if there is no handler for the URL
        """
        response = None
        
        for rule, handler in handlers:
            params = rule.match(request)
            if params is None:
                continue
            
            this_result = handler(self, **params)
            if this_result is None:
                continue
            
            if response is None:
                response = Response(status_code=rule.status_code)
            response.append(this_result)

        return response


    def slowapi_include(self, app):
        """append another App for the composite
        Parameters:
          - api: an instance of App
        """

        if not hasattr(self, 'slowapi_composite_apps'):
            App.__init__(self)  # in case this is forgotten in user subclass...
        
        self.slowapi_composite_apps.append(app)
        

    def slowapi_included(self):
        return self.slowapi_composite_apps
        

    def slowapi_get(self, request:Request) -> Response:
        if not hasattr(self, 'slowapi_get_handlers'):
            App.__init__(self)  # in case this is forgotten in user subclass...
        if type(request) is str:
            request = Request(request)
            
        response = Response()
        response.append(self._slowapi_handle_request(self.slowapi_get_handlers, request))
        for app in self.slowapi_composite_apps:
            response.append(app.slowapi_get(request))
            
        return response
        

    def slowapi_post(self, request:Request, body:bytes=None) -> Response:
        if not hasattr(self, 'slowapi_post_handlers'):
            App.__init__(self)  # in case this is forgotten in user subclass...
        if type(request) is str:
            request = Request(request)
        if body is not None:
            request.body = body
                    
        response = Response()
        response.append(self._slowapi_handle_request(self.slowapi_post_handlers, request))
        for app in self.slowapi_composite_apps:
            response.append(app.slowapi_post(request))
            
        return response
    

    def slowapi_delete(self, request:Request) -> Response:
        if not hasattr(self, 'slowapi_delete_handlers'):
            App.__init__(self)  # in case this is forgotten in user subclass...
        if type(request) is str:
            request = Request(request)
            
        response = Response()
        response.append(self._slowapi_handle_request(self.slowapi_delete_handlers, request))
        for app in self.slowapi_composite_apps:
            response.append(app.slowapi_delete(request))

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
            response = self.slowapi_get(url)
            
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
            request.body = environ['wsgi.input'].read(content_length)
            response = self.slowapi_post(request)
        
        elif method == 'DELETE':
            response = self.slowapi_delete(request)
            
        else:
            start_response('500 Internal Server Error', [])
            return [ b'' ]

    
        if response is None:
            start_response('404 Not Found', [])
            return [ b'' ]

        start_response(response.get_status(), response.get_headers())
        return [ response.get_content() ]


    def run(self, **kwargs):
        kwargs['port'] = kwargs.get('port', 8000)
        kwargs['api_path'] = kwargs.get('api_path', None)
        kwargs['webfile_dir'] = kwargs.get('webfile_dir', None)
        run_server(self, **kwargs)
