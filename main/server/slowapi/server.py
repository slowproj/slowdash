# Created by Sanshiro Enomoto on 11 January 2025 #

"""HTTP Server that can handle both SlowAPI and GET-request for files at the same time
"""


import sys, os, logging, functools, base64, traceback
from urllib.parse import urlparse, unquote
from http.server import HTTPServer, BaseHTTPRequestHandler

bcrypt_imported = False  # modudle not necessary unless authorization is enabled



class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, app, api_path, webfile_dir, index_file, auth_list, *args, **kwargs):
        self.app = app
        self.api_path = api_path
        self.webfile_dir = webfile_dir
        self.index_file = index_file
        self.auth_list = auth_list

        if api_path is None and webfile_dir is not None:
            logging.error(f'SlowAPI_Server: "api_path" must not be None if "webfile" is used')
        
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

        
    # avoid DNS lookup #
    def address_string(self):
        host, port = self.client_address[:2]
        return host

    # disable the standard log messaging #
    def log_message(self, format, *args):
        pass

    
    def do_GET(self):        
        if not self._check_auth():
            self._request_auth()
            return

        api_url, file_path = self._parse_url()
        try:
            if api_url is not None:
                response = self.app.slowapi(api_url)
            elif file_path is not None:
                self._process_file_get(file_path)
                return
            else:
                self._reply_error(400)  # Bad Request
                return
        except Exception as e:
            logging.error(f'SlowAPI_Server: {e}')
            logging.error(traceback.format_exc())
            self._reply_error(400)  # Bad Request
            return

        self._reply_response(response)
            
                         
    def do_POST(self):
        if not self._check_auth():
            self._request_auth()
            return
            
        api_url, file_path = self._parse_url()
        if api_url is None:
            self._reply_error(400)  # Bad Request
            return
        
        try:
            content_length = int(self.headers.get('content-length', 0))
            if content_length > 1024*1024*1024:
                self._reply_error(507)   # Insufficient Storage (WebDAV)
                return
            request = slowapi.Request(api_url, method='POST', body=self.rfile.read(content_length))
            response = self.app.slowapi(request)
        except Exception as e:
            logging.error(f'SlowAPI_Server: {e}')
            logging.error(traceback.format_exc())
            self._reply_error(400)  # Bad Request
            return

        self._reply_response(response)

        
    def do_DELETE(self):
        if not self._check_auth():
            self._request_auth()
            return
            
        api_url, file_path = self._parse_url()
        if api_url is None:
            self._reply_error(400)  # Bad Request
            return
        
        try:
            request = slowapi.Request(api_url, method='DELETE')
            response = self.app.slowapi(request)
        except Exception as e:
            logging.error(f'SlowAPI_Server: {e}')
            logging.error(traceback.format_exc())
            self._reply_error(400)  # Bad Request
            return

        self._reply_response(response)

            
    def _check_auth(self):
        if self.auth_list is None:
            return True
        
        auth = self.headers.get('Authorization', None)
        if auth == '' or auth is None:
            return False

        global bcrypt_imported
        if not bcrypt_imported:
            try:
                import bcrypt
                bcrypt_imported = True
            except:
                logging.error('SlowAPI_Server: missing python module "bcrypt"')
                return False
        
        try:
            user, word = tuple(base64.b64decode(auth.split(' ')[1]).decode().split(':'))
            if word is None:
                return False
            true_key = self.auth_list.get(user, None)
            if true_key is None:
                return False
            if word == true_key:
                return True
            
            key = bcrypt.hashpw(word.encode("utf-8"), true_key.encode()).decode("utf-8")
            if key == true_key:
                self.auth_list[user] = word
                return True
            
        except Exception as e:
            logging.warning(f'SlowAPI_Server: Authentication Error: {str(e)}')
            
        return False

    
    def _request_auth(self):
        self.send_response(401)   # Unauthorized
        self.send_header('WWW-Authenticate', 'Basic realm="SlowAPI App"')
        self.end_headers()
        logging.debug(f'SlowAPI_Server: AUTH request')


    def _parse_url(self):
        url = urlparse(self.path)

        path = [ unquote(p) for p in url.path.split('/') ]
        while path.count(''):
            path.remove('')

        api_url, file_path = None, None
        if self.api_path is not None:
            if len(path) > 0 and path[0] == self.api_path:
                api_url = '/'.join(path[1:])
        elif self.webfile_dir is None:
            api_url = '/'.join(path)
            
        if api_url is not None:
            if len(url.query) > 0:
                api_url += '?' + url.query
            if len(url.fragment) > 0:
                api_url += '#' + url.fragment
        elif self.webfile_dir is not None:
            if path.count('..'):
                file_path = None  # invalid
            elif len(path) == 0:
                file_path = ''
            else:
                file_path = os.path.join(*path)

        return api_url, file_path

                
    def _process_file_get(self, path):
        if len(path) == 0:
            if self.index_file is not None:
                path = self.index_file
            else:
                if True:
                    self.send_response(200)   # OK
                    self.send_header('content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b'<!DOCTYPE html>\r\n')
                    self.wfile.write(b'<html><body><h3>SlowAPI Server</h3></body></html>')
                    self.wfile.flush()
                else:
                    self.send_error(404)   # Not Found
                return
        
        filepath = os.path.join(self.webfile_dir, path)
        if not os.path.isfile(filepath):
            logging.warning(f'SlowAPI_Server: FILE_GET: not a file: {filepath}')
            self.send_error(404)   # Not Found
            return
        if not os.access(filepath, os.R_OK):
            logging.warning(f'SlowAPI_Server: FILE_GET: permission denied: {filepath}')
            self.send_error(404)   # Not Found
            return
        
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
            return

        try:
            self.send_response(200)   # OK
            self.send_header('content-type', content_type)
            self.end_headers()
            self.wfile.write(open(filepath, 'rb', buffering=0).readall())
            self.wfile.flush()
        except Exception as e:
            logging.warning(f'Error on sending a reply (browser closed?): {e}')

        
    def _send_response(self, response):
        if response is None:
            self.send_error(404)   # Not Found
            return

        status_code = response.get_status_code()
        if status_code >= 400:
            self.send_error(status_code)
            return
        else:
            self.send_response(status_code)

        for k, v in response.get_headers():
            self.send_header(k, v)
        self.end_headers()

        content = response.get_content()
        if content is not None:
                self.wfile.write(content)
                self.wfile.flush()

                
    def _reply_response(self, response):
        try:
            self._send_response(response)
        except Exception as e:
            logging.warning(f'Error on sending a reply (browser closed?): {e}')

        
    def _reply_error(self, status_code):
        try:
            self.send_error(status_code)
        except Exception as e:
            logging.warning(f'Error on sending a reply (browser closed?): {e}')

        

        
import signal
def signal_handler(signum, frame):
    raise InterruptedError


def run(app, port, api_path='api', webfile_dir='.', index_file=None, auth_list=None):
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        httpserver = HTTPServer(
            ('', port),
            functools.partial(RequestHandler, app, api_path, webfile_dir, index_file, auth_list)
        )
    except Exception as e:
        sys.stderr.write('ERROR: %s\n' % str(e))
        sys.stderr.write(traceback.format_exc())
        return -1

    sys.stderr.write('Listening at port %d\n' % port)
    try:
        httpserver.serve_forever()
    except KeyboardInterrupt:
        pass
    except InterruptedError:
        pass

    sys.stderr.write('Terminated\n')    
    try:
        httpserver.shutdown()
    except:
        pass

    httpserver.server_close()
