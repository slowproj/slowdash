# Created by Sanshiro Enomoto on 10 January 2025 #


import sys, os, copy, json, asyncio, logging
from decimal import Decimal


class Response:
    status = {
        200: 'OK', 201: 'Created',
        400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found',
        500: 'Internal Server Error', 503: 'Service Unavailable',
    }

    
    @staticmethod
    def json_defaults(obj):
        """The "default" function for json.dumps()
        """
        if isinstance(obj, Decimal):
            return int(obj) if float(obj).is_integer() else float(obj)

        
    def __init__(self, status_code=0, *, content_type=None, content=None):
        self.status_code = status_code
        self.content_type = content_type
        self.content = None
        self.headers = {}
        
        if content is not None:
            if status_code == 0:
                self.status_code = 200
            if content_type is None:
                self.merge_content(content)
            else:
                self.content_type = content_type
                self.content = content


    def merge_response(self, response) -> None:
        """Merges a response into "self".
           This method can be overriden, especially by a custom Response from a "middleware" App.
        Args:
          - response: a response object to merge
        Note:
          - The default behavior is:
            - If status_code is different, take the content with a larger status code
            - For equal status_code, self.append() the response content
        """
        if self.status_code < response.status_code:
            self.status_code = response.status_code
            self.content_type = response.content_type
            self.content = response.content
            self.headers = copy.deepcopy(response.headers)
        
        elif self.status_code == response.status_code:
            self.merge_content(response.content)
            self.headers.update(response.headers)

            
    def merge_content(self, content):
        if content is None:
            # no content to append
            pass
        
        elif isinstance(content, Response):
            self.merge_content(content)
        
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
                logging.error(f'  dest: {self.content}')
                logging.error(f'  src: {content}')
            
        else:
            if self.content is None:
                self.content = content
            else:
                logging.error(f'SlowAPI: invalid content type to append ({type(content)})')

                
    def get_status_code(self) -> int:
        if self.status_code == 0:
            return 404
        else:
            return self.status_code
            
        
    def get_status(self) -> str:
        if self.status_code == 0:
            return f'404 {self.status[404]}'
        else:
            return '%d %s' % (self.status_code, self.status.get(self.status_code, 'Unknown Response'))
            
        
    def get_headers(self):
        headers = [ (k,v) for k,v in self.headers.items() if k.upper() != 'CONTENT-TYPE' ]

        if self.content_type is not None:
            headers.append(('Content-Type',  self.content_type))
            if type(self.content) is bytes:
                if 'CONTENT_LENGTH' not in [ k.upper() for k in self.headers ]:
                    headers.append(('Content-Length', str(len(self.content))))

        return headers
            
        
    def get_content(self, json_kwargs={}) -> bytes:
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
            try:
                return self.get_content().decode()
            except:
                return f'[Binary File ({self.get_headers()})]'



class FileResponse(Response):
    """SlowAPI Response that returns the content of a file
    Note:
      - Sanity checks must be made before using this.
    """
        
    def __init__(self, filepath:str=None, *, content_type=None):
        """
        Note: for async load, use await FileResponse().load(filepath)
        """
        if filepath is not None:
            content_type, content = read_file(filepath, content_type)
            if content is None:
                super().__init__(400)
            else:
                super().__init__(200, content_type=content_type, content=content)


    async def load(self, filepath:str, *, content_type=None):
        content_type, content = await asyncio.to_thread(read_file, filepath, content_type)
        if content is None:
            super().__init__(400)
        else:
            super().__init__(200, content_type=content_type, content=content)

        return self


def read_file(filepath, content_type):
    if not os.path.isfile(filepath):
        logging.warning(f'SlowAPI_FileResponse: not a file: {filepath}')
        return None, None
    if not os.access(filepath, os.R_OK):
        logging.warning(f'SlowAPI_FileResponse: permission denied: {filepath}')
        return None, None

    content = None
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
    except Exception as e:
        logging.warning(f'SlowAPI_FileResponse: system error: {filepath}: {e}')
        return None, None

    if content_type is None:
        ext = os.path.splitext(filepath)[1]
        if ext == '.html':
            content_type = 'text/html'
        elif ext in ['.js', '.mjs']:
            content_type = 'text/javascript'
        elif ext == '.css':
            content_type = 'text/css'
        elif ext == 'json':
            content_type = 'application/json'
        elif ext == '.png':
            content_type = 'image/png'
        elif ext == '.svg':
            content_type = 'image/svg+xml'
        elif ext in ['.jpg', '.jpeg']:
            content_type = 'image/jpeg'
        elif ext == '.pdf':
            content_type = 'application/pdf'
        elif ext in ['.txt', '.py']:
            content_type = 'text/plain'
        else:
            content_type = 'application/octet-stream'

    return (content_type, content)

