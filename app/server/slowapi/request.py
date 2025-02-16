# Created by Sanshiro Enomoto on 11 January 2025 #

import copy, logging
from urllib.parse import urlparse, parse_qsl, unquote


class Request:
    is_async = True  # True for ASGI; WSGI will change this directly
    
    def __init__(self, url, method="GET", *, headers={}, body=None):
        self.method = method.upper()
        self.headers = copy.deepcopy(headers)
        self.body = body
        
        self.aborted = False

        u = urlparse(url)
        self.path = [ unquote(p) for p in u.path.split('/') ]
        self.query = { unquote(key): unquote(value) for key, value in parse_qsl(u.query) }
        while self.path.count(''):
            self.path.remove('')


    def abort(self):
        self.aborted = True


    def __str__(self):
        return f"{self.method} /{'/'.join(self.path)}{'?' if len(self.query)>0 else ''}{'&'.join(['%s=%s'%(k,v) for k,v in self.query.items()])}"
