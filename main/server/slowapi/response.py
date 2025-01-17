# Created by Sanshiro Enomoto on 10 January 2025 #


import json, logging
from decimal import Decimal


class Response:
    status = {
        200: 'OK', 201: 'Created',
        400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found',
        500: 'Internal Server Error', 503: 'Service Unavailable',
    }

    
    @staticmethod
    def json_defaults(obj):
        if isinstance(obj, Decimal):
            return int(obj) if float(obj).is_integer() else float(obj)

                
    def __init__(self, status_code=0, *, content_type=None, content=None):
        self.status_code = status_code
        self.content_type = content_type
        self.content = None
        
        if content is not None:
            if status_code == 0:
                self.status_code = 200
            if content_type is None:
                self.append(content)
            else:
                self.content_type = content_type
                self.content = content

                
    def append(self, content):
        if content is None:
            # no content to append
            pass
        
        elif isinstance(content, Response):
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
            if self.content is None:
                self.content = content
            else:
                logging.error(f'SlowAPI: invalid content type to append ({type(content)})')

            
    def get_status_code(self):
        if self.status_code == 0:
            return 404
        else:
            return self.status_code
            
        
    def get_status(self):
        if self.status_code == 0:
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
            return b''
        
        if type(self.content) is bytes:
            return self.content
            
        elif type(self.content) is str:
            return self.content.encode()
            
        else:
            kwargs = { 'default': self.json_defaults }
            kwargs.update(json_kwargs)

            try:
                return json.dumps(self.content, **kwargs).encode()
            except:
                return str(self.content).encode()


    def __str__(self):
        if self.get_status_code() >= 400:
            return self.get_status()
        else:
            return self.get_content(json_kwargs={"indent":4}).decode()
