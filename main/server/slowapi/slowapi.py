# Created by Sanshiro Enomoto on 10 January 2025 #


import typing, json, logging
from urllib.parse import urlparse, parse_qsl, unquote
import inspect


response_status = {
    200: 'OK', 201: 'Created',
    400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found',
    500: 'Internal Server Error', 503: 'Service Unavailable',
}



class Rule:
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
                    value = attr.annotation(value)
                except Exception as e:
                    print(e)
                    # invalid parameter type
                    return None
            kwargs[pname] = value

        if self.body_param is not None:
            kwargs[self.body_param] = body

        logging.debug(kwargs)
            
        return kwargs
    


class Response:
    def __init__(self, status_code:int=200, content_type=None, content=None):
        self.status_code = status_code
        self.content_type = content_type
        self.content = None

        if content is not None:
            if content_type is None:
                self.append(content)
            else:
                self.set_content(content_type, content)

                
    def append(self, content):
        if type(content) is list:
            if self.content is None:
                self.content = []
                self.content_type = 'application/json'
            if type(self.content) is list:
                self.content.extend(content)
            else:
                logging.error('SlowAPI: incompatible results cannot be combined (list)')
                
        elif type(content) is dict:
            if self.content is None:
                self.content = {}
                self.content_type = 'application/json'
            if type(self.content) is dict:
                self.content.update(content)
            else:
                logging.error('SlowAPI: incompatible results cannot be combined (dict)')
                
        elif type(content) is str:
            if self.content is None:
                self.content = ''
                self.content_type = 'text/plain'
            if type(self.content) is str:
                self.content += content
            else:
                logging.error('SlowAPI: incompatible results cannot be combined (dict)')
            
        else:
            logging.error('SlowAPI: invalid content type to append')

            
    def set_content(self, content_type:str, content:bytes):
        if self.content is not None:
            logging.error('SlowAPI:Response: reply content already set')
            return

        self.content_type = content_type
        self.content = content

            
    def get_status_code(self):
        if self.content is None:
            return 404
        else:
            return self.status_code
            
        
    def get_status(self):
        if self.content is None:
            return '404 Not Found'
        else:
            return '%d %s' % (self.status_code, response_status.get(self.status_code, 'Unknown Response'))
            
        
    def get_content_type(self):
        if self.content_type is None:
            return ''
        else:
            return self.content_type
            
        
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
        return f'Status: {self.get_status()}\nContent-type: {self.get_content_type()}\n{self.get_content({"indent":4}).decode()}\n'

    
        
class SlowAPI:
    def __init__(self):
        self.get_handlers = None
        self.post_handlers = None
        self.delete_handlers = None

    
    @staticmethod
    def get(rule:str, status_code:int=200):
        def decorator(func):
            func.slowapi_get_rule = Rule(rule, inspect.signature(func), status_code=status_code)
            return func
        return decorator


    @staticmethod
    def post(rule:str, status_code:int=201):
        def decorator(func):
            func.slowapi_post_rule = Rule(rule, inspect.signature(func), status_code=status_code)
            return func
        return decorator


    @staticmethod
    def delete(rule:str, status_code:int=200):
        def decorator(func):
            func.slowapi_delete_rule = Rule(rule, inspect.signature(func), status_code=status_code)
            return func
        return decorator


    def handle_get_request(self, url:str):
        if self.post_handlers is None:
            self._build_handler_table()

        return self._handle_request(self.get_handlers, url)
    

    def handle_post_request(self, url:str, body:bytes):
        if self.post_handlers is None:
            self._build_handler_table()

        return self._handle_request(self.post_handlers, url, body)
    

    def handle_delete_request(self, url:str):
        if self.delete_handlers is None:
            self._build_handler_table()

        return self._handle_request(self.delete_handlers, url)


    def _build_handler_table(self):
        self.get_handlers = []
        self.post_handlers = []
        self.delete_handlers = []
        
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
                

    def _handle_request(self, handlers, url:str, body:bytes=None):
        path, opts = Rule.decode_url(url)
        response = None
        
        for rule, handler in handlers:
            params = rule.match(path, opts, body)
            if params is None:
                continue
            
            this_result = handler(self, **params)
            if this_result is None:
                continue
            if type(this_result) is Response:
                return this_result  # no result aggregation

            if response is None:
                response = Response(status_code=rule.status_code, content=this_result)
            else:
                response.append(this_result)

        if response is None:
            return Response(status_code=404)
        else:
            return response
