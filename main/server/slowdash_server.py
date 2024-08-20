#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 2 November 2017 #


import sys, os, json, logging, collections, subprocess, functools, socket, traceback
from urllib.parse import urlparse, parse_qsl

from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

from slowdash import WebUI

import base64
bcrypt_imported = False  # modudle not necessary unless authorization is enabled


class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, webui, cgi_name, web_path, index_file, *args, **kwargs):
        self.webui = webui
        self.cgi_name = cgi_name
        self.web_path = web_path
        self.index_file = index_file

        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

        
    # avoid DNS lookup #
    def address_string(self):
        host, port = self.client_address[:2]
        return host

    # disable the standard log messaging #
    def log_message(self, format, *args):
        pass

    
    def do_GET(self):
        sys.stderr.write('GET: %s ...' % self.path)

        if not self.check_auth():
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="SlowDash"')
            self.end_headers()
            sys.stderr.write('AUTH\n')
            return
            
        url = urlparse(self.path)
        path_split = url.path.split('/')
        while path_split.count(''):
            path_split.remove('')
        if path_split.count('..'):
            self.send_error(403)
            sys.stderr.write('ERROR\n')
            return

        if (len(path_split) == 0):
            path_split.append(self.index_file)

        try:
            if path_split[0] == self.cgi_name or path_split[0] == 'api':
                url_recon = '/'.join(path_split[1:])
                if len(url.query) > 0:
                    url_recon = '%s?%s' % (url_recon, url.query)
                if len(url.fragment) > 0:
                    url_recon = '%s#%s' % (url_recon, url.fragment)
                self.process_cgi_get(url_recon)
            else:
                self.process_file_get(
                    os.path.join(self.web_path, '/'.join(path_split))
                )
            sys.stderr.write('done\n')
        except Exception as e:
            logging.warn("slowdash_server: do_GET(): %s" % str(e))
            logging.warn(traceback.format_exc())
            sys.stderr.write('ERROR\n')

                         
    def do_POST(self):
        sys.stderr.write('POST: %s\n' % self.path)
        
        if not self.check_auth():
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="SlowDash"')
            self.end_headers()
            return
        
        url = urlparse(self.path)
        path_split = url.path.split('/')
        while path_split.count(''):
            path_split.remove('')
        if path_split.count('..'):
            self.send_error(403)
            return
        if (len(path_split) < 2) or (path_split[0] != self.cgi_name and path_split[0] != 'api'):
            self.send_error(403)
            return
        url_recon = '/'.join(path_split[1:])
        if len(url.query) > 0:
            url_recon = '%s?%s' % (url_recon, url.query)
        
        try:
            content_length = int(self.headers['content-length'])
        except:
            self.send_error(400)
            return
        if content_length > 1024*1024*1024:
            self.send_error(507)
            return
        doc = self.rfile.read(content_length)
        
        result = self.webui.process_post_request(url_recon, doc)
        if (result is None):
            self.send_error(500)
            return
        if result.response >= 400:
            self.send_error(result.response)
            return
        if result.content_type is None:
            self.send_response(result.response)
            self.end_headers()
            self.wfile.flush()
            return

        try:
            self.send_response(result.response)
            self.send_header('content-type', result.content_type)
            self.end_headers()
            result.write_to(self.wfile).destroy()
            self.wfile.flush()
        except Exception as e:
            logging.warn("slowdash_server: do_POST(): %s" % str(e))
            logging.warn(traceback.format_exc())

    
    def do_DELETE(self):
        sys.stderr.write('DELETE: %s\n' % self.path)
        
        if not self.check_auth():
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="SlowDash"')
            self.end_headers()
            return
        
        url = urlparse(self.path)
        path_split = url.path.split('/')
        while path_split.count(''):
            path_split.remove('')
        if path_split.count('..'):
            self.send_error(403)
            return
        if (len(path_split) < 2) or (path_split[0] != self.cgi_name and path_split[0] != 'api'):
            self.send_error(403)
            return
        url_recon = '/'.join(path_split[1:])
        if len(url.query) > 0:
            url_recon = '%s?%s' % (url_recon, url.query)
        
        result = self.webui.process_delete_request(url_recon)
        if (result is None):
            self.send_error(500)
            return
        if result.response >= 400:
            self.send_error(result.response)
            return
        
        self.send_response(result.response)
        self.end_headers()

            
    def check_auth(self):
        if self.webui.auth_list is None:
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
                logging.error('install python module "bcrypt"')
                return False
        
        try:
            user, word = tuple(base64.b64decode(auth.split(' ')[1]).decode().split(':'))
            if word is None:
                return False
            true_key = self.webui.auth_list.get(user, None)
            if true_key is None:
                return False
            if word == true_key:
                return True
            
            key = bcrypt.hashpw(word.encode("utf-8"), true_key.encode()).decode("utf-8")
            if key == true_key:
                self.webui.auth_list[user] = word
                return True
            
        except Exception as e:
            sys.stderr.write("Authentication Error: %s" % str(e))
            
        return False

        
    def process_cgi_get(self, url):
        result = self.webui.process_get_request(url)
        if (
            (result is None) or
            (result.content_type is None) or
            ((result.content is None) and (result.content_readable is None))
        ):
            self.send_error(500)
            return
        if result.response >= 400:
            self.send_error(result.response)
            return

        self.send_response(result.response)
        self.send_header('content-type', result.content_type)
        self.end_headers()
        result.write_to(self.wfile).destroy()
        self.wfile.flush()

        
    def process_file_get(self, filepath):
        if not os.path.isfile(filepath):
            self.send_error(404)
            return
        if not os.access(filepath, os.R_OK):
            self.send_error(404)
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
        elif ext == '.txt':
            content_type = 'text/plain'
        else:
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header('content-type', content_type)
        self.end_headers()
        self.wfile.write(open(filepath, 'rb', buffering=0).readall())
        self.wfile.flush()


        


import signal
def signal_handler(signum, frame):
    raise InterruptedError
signal.signal(signal.SIGTERM, signal_handler)


def start(port, webui, cgi_name, web_path, index_file):
    try:
        httpserver = HTTPServer(
            ('', port),
            functools.partial(RequestHandler, webui, cgi_name, web_path, index_file)
        )
    except Exception as e:
        sys.stderr.write('ERROR: %s\n' % str(e))
        logging.error(traceback.format_exc())
        return -1

    sys.stderr.write('listening at port %d\n' % port)

    try:
        httpserver.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write('Terminated\n')
    except InterruptedError:
        sys.stderr.write('Terminated\n')

    try:
        httpserver.shutdown()
    except:
        pass
        
    httpserver.server_close()
    webui.close()
    
    return 0
    


from optparse import OptionParser

if __name__ == '__main__':
    default_web_port = 18881
    cgi_name = 'slowdash.cgi'
    index_file = 'slowhome.html'
    sys_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))
    web_path = os.path.join(sys_dir, 'web')
    
    optionparser = OptionParser()
    optionparser.add_option(
        '-p', '--port',
        action='store', dest='port', type='int', default=default_web_port,
        help='port number, default default_port'
    )
    (options, args) = optionparser.parse_args()
    
    webui = WebUI()
    if webui.app is None:
        sys.exit(-1)

    start(options.port, webui, cgi_name, web_path, index_file)
