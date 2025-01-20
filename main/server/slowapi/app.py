# Created by Sanshiro Enomoto on 19 January 2025 #

import logging


from .router import Router
from .server import wsgi, serve_wsgi


class App:
    """SlowAPI App for WSGI
    Note:
      - User App can be derived from this class, or can be passed to the constructor parameter:
        - Method 1: class MyApp(slowapi.App)  then  app = MyApp()
        - Method 2: app = slowapi.App(MyApp())
      - In either case,
        - MyApp can use the SlowAPI routing decorators.
        - The app object implements WSGI.
        - Sub-apps can be added by app.slowapi.include(MySubApp()).
        - Middlewares can be added by app.slowapi.add_middleware(...)
    """
    
    def __init__(self, subapp=None):
        if not hasattr(self, 'slowapi'): # subclass might have defnied a custom router
            self.slowapi = Router(self)
            
        if subapp is not None:
            self.slowapi.include(subapp)
            
            
    def __call__(self, environ, start_response):
        """WSGI entry point
        """
        if not hasattr(self, 'slowapi'): # __init__() might not have been called
            self.slowapi = Router(self)
            
        return wsgi(self, environ, start_response)
    

    def run(self, port=8000):
        """Run HTTP Server
        """
        serve_wsgi(self, port)



class AsyncApp(App):
    # ASGI App: to be implemeted
    pass
