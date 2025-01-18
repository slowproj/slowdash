# Created by Sanshiro Enomoto on 11 January 2025 #

import copy, logging
from urllib.parse import urlparse, parse_qsl, unquote


class Request:
    def __init__(self, url, method="GET", *, headers={}, body=None):
        self.url = url
        self.method = method.upper()
        self.headers = copy.deepcopy(headers)
        self.body = body

        self.aborted = False

        u = urlparse(self.url)
        self.path = [ unquote(p) for p in u.path.split('/') ]
        self.query = { unquote(key): unquote(value) for key, value in parse_qsl(u.query) }
        self.fragment = u.fragment
        
        while self.path.count(''):
            self.path.remove('')


    def abort(self):
        self.aborted = True
