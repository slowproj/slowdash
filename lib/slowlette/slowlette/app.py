# Created by Sanshiro Enomoto on 19 January 2025 #

import asyncio, inspect, logging

from .router import Router, PathRule
from .server import dispatch_asgi, dispatch_wsgi, serve_asgi, serve_wsgi


class App:
    """Slowlette App for ASGI
    Note:
      - User App can be derived from this class, or can be passed to the constructor parameter:
        - Method 1: class MyApp(slowlette.App)  then  app = MyApp()
        - Method 2: app = slowlette.App(MyApp())
      - In either case,
        - MyApp can use the Slowlette routing decorators.
        - The app object implements ASGI.
        - Sub-apps can be added by app.slowlette.include(MySubApp()).
        - Middlewares can be added by app.slowlette.add_middleware(...)
    """
    
    def __init__(self, subapp=None):
        if not hasattr(self, 'slowlette'): # subclass might have defnied a custom router
            self.slowlette = Router(self)
            
        if subapp is not None:
            self.slowlette.include(subapp)
            
            
    async def __call__(self, scope, receive, send):
        """ASGI entry point
        """
        if not hasattr(self, 'slowlette'): # __init__() might not have been called
            self.slowlette = Router(self)

        await dispatch_asgi(self, scope, receive, send)
    

    def run(self, port=8000, **kwargs):
        """Run HTTP Server
        """
        serve_asgi(self, port, **kwargs)



class Slowlette(App):
    """Slowlette App that can assign URL endpoints to functions, instead of class methods
    """
    
    class FunctionAdapter:
        def __init__(self, func):
            self.func = func
        async def __call__(self, app, *args, **kwargs):
            result = self.func(*args, **kwargs)
            if inspect.isawaitable(result):
                return await result
            else:
                return result

    def __init__(self):
        super().__init__()


    def get(self, path_rule:str, status_code:int=200):
        """decorator to make a GET-request handler (Python function)
        Args:
            - path_rule: path pattern to match
            - status_code: default status code for success
        """
        def wrapper(func):
            adapter = self.FunctionAdapter(func)
            adapter.slowlette_path_rule = PathRule(path_rule, 'GET', func, status_code=status_code)
            self.slowlette.handlers.append(adapter)
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
            adapter.slowlette_path_rule = PathRule(path_rule, 'POST', func, status_code=status_code)
            self.slowlette.handlers.append(adapter)
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
            adapter.slowlette_path_rule = PathRule(path_rule, 'DELETE', func, status_code=status_code)
            self.slowlette.handlers.append(adapter)
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
            adapter.slowlette_path_rule = PathRule(path_rule, '*', func, status_code=status_code)
            self.slowlette.handlers.append(adapter)
            return func
        return wrapper
