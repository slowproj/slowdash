# Created by Sanshiro Enomoto on 19 January 2025 #

import inspect, logging

from .router import Router, PathRule
from .server import dispatch_asgi, dispatch_wsgi, serve_asgi, serve_wsgi


class App:
    """SlowAPI App for ASIG
    Note:
      - User App can be derived from this class, or can be passed to the constructor parameter:
        - Method 1: class MyApp(slowapi.App)  then  app = MyApp()
        - Method 2: app = slowapi.App(MyApp())
      - In either case,
        - MyApp can use the SlowAPI routing decorators.
        - The app object implements ASGI.
        - Sub-apps can be added by app.slowapi.include(MySubApp()).
        - Middlewares can be added by app.slowapi.add_middleware(...)
    """
    
    def __init__(self, subapp=None):
        if not hasattr(self, 'slowapi'): # subclass might have defnied a custom router
            self.slowapi = Router(self)
            
        if subapp is not None:
            self.slowapi.include(subapp)
            
            
    async def __call__(self, scope, receive, send):
        """ASGI entry point
        """
        if not hasattr(self, 'slowapi'): # __init__() might not have been called
            self.slowapi = Router(self)

        await dispatch_asgi(self, scope, receive, send)
    

    def run(self, port=8000, **kwargs):
        """Run HTTP Server
        """
        serve_asgi(self, port, **kwargs)



class SlowAPI(App):
    """SlowAPI App that can assign URL endpoints to functions, instead of class methods
    """
    
    class FunctionAdapter:
        def __init__(self, func):
            self.func = func
        def __call__(self, *args, **kwargs):
            return self.func(*args, **kwargs)

        
    def __init__(self):
        super().__init__()
        self.slowapi_function_handlers = []


    def get(self, path_rule:str, status_code:int=200):
        """decorator to make a GET-request handler (Python function)
        Args:
            - path_rule: path pattern to match
            - status_code: default status code for success
        """
        def wrapper(func):
            adapter = self.FunctionAdapter(func)
            adapter.slowapi_path_rule = PathRule(path_rule, 'GET', inspect.signature(func), status_code=status_code)
            self.slowapi.handlers.append(adapter)
            return func
        return wrapper

    
    def post(self, path_rule:str, status_code:int=200):
        """decorator to make a POST-request handler (Python function)
        Args:
            - path_rule: path pattern to match
            - status_code: default status code for success
        """
        def wrapper(func):
            adapter = self.FunctionAdapter(func)
            adapter.slowapi_path_rule = PathRule(path_rule, 'POST', inspect.signature(func), status_code=status_code)
            self.slowapi.handlers.append(adapter)
            return func
        return wrapper

    
    def delete(self, path_rule:str, status_code:int=200):
        """decorator to make a DELETE-request handler (Python function)
        Args:
            - path_rule: path pattern to match
            - status_code: default status code for success
        """
        def wrapper(func):
            adapter = self.FunctionAdapter(func)
            adapter.slowapi_path_rule = PathRule(path_rule, 'DELETE', inspect.signature(func), status_code=status_code)
            self.slowapi.handlers.append(adapter)
            return func
        return wrapper

    
    def route(self, path_rule:str, status_code:int=200):
        """decorator to make a request handler (Python function) for all request methods
        Args:
            - path_rule: path pattern to match
            - status_code: default status code for success
        """
        def wrapper(func):
            adapter = self.FunctionAdapter(func)
            adapter.slowapi_path_rule = PathRule(path_rule, '*', inspect.signature(func), status_code=status_code)
            self.slowapi.handlers.append(adapter)
            return func
        return wrapper
